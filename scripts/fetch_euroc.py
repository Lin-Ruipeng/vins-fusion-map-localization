#!/usr/bin/env python3
"""Read official ZIP metadata with verified HTTP ranges, fetch selected members.

The complete ETH machine_hall archive is 12.7 GB. Selecting individual members
preserves the ZIP CRC integrity check without downloading unrelated sequences.
"""
import argparse
import concurrent.futures
import io
import json
import os
import re
import shutil
import struct
import time
import urllib.request
import zipfile
import zlib
from pathlib import Path

OFFICIAL = 'https://www.research-collection.ethz.ch/server/api/core/bitstreams/7b2419c1-62b5-4714-b7f8-485e5fe3e5fe/content'
MIRROR = 'https://huggingface.co/datasets/GlowBond/EuRoC_MAV_Dataset/resolve/main/machine_hall.zip?download=true'
SOURCES = [OFFICIAL, MIRROR] if os.environ.get('EUROC_SOURCE') == 'official' else [MIRROR, OFFICIAL]
SIZE = 12683729426
LAB = Path(__file__).resolve().parent.parent

def get_range(start, end):
    for attempt in range(6):
        try:
            req = urllib.request.Request(SOURCES[attempt % len(SOURCES)], headers={
                'User-Agent': 'Mozilla/5.0', 'Range': f'bytes={start}-{end}'})
            with urllib.request.urlopen(req, timeout=90) as response:
                expected = f'bytes {start}-{end}/{SIZE}'
                if response.status != 206 or response.headers.get('Content-Range') != expected:
                    raise RuntimeError('HTTP range was not honored: ' + str(response.headers.get('Content-Range')))
                content = response.read()
                if len(content) != end - start + 1:
                    raise RuntimeError('Truncated HTTP range')
                return content
        except Exception as error:
            if attempt == 5:
                raise
            print(f'Retry range {start}-{end}: {error}', flush=True)
            time.sleep(min(2 ** attempt, 16))

class RemoteZipFile(io.RawIOBase):
    def __init__(self):
        self.position = 0
        (LAB / 'downloads').mkdir(parents=True, exist_ok=True)
        cached = LAB / 'downloads/machine_hall_tail.bin'
        self.tail = cached.read_bytes() if cached.exists() else get_range(SIZE - 65536, SIZE - 1)
        if not cached.exists():
            cached.write_bytes(self.tail)

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset + (self.position if whence == 1 else SIZE if whence == 2 else 0)
        return self.position

    def read(self, count=-1):
        if count < 0:
            count = SIZE - self.position
        count = min(count, SIZE - self.position)
        if count <= 0:
            return b''
        start = self.position
        if start >= SIZE - len(self.tail):
            content = self.tail[start - (SIZE - len(self.tail)):start - (SIZE - len(self.tail)) + count]
        else:
            content = get_range(start, start + count - 1)
        self.position += len(content)
        return content

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--member', action='append', default=[])
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    print('SOURCES', SOURCES, flush=True)
    with zipfile.ZipFile(RemoteZipFile()) as archive:
        metadata = [{key: getattr(info, key) for key in (
            'filename', 'file_size', 'compress_size', 'compress_type', 'CRC', 'header_offset')}
                    for info in archive.infolist()]
        (LAB / 'downloads/machine_hall_index.json').write_text(json.dumps(metadata, indent=2))
        for info in archive.infolist():
            print(f'{info.filename} {info.file_size} compressed={info.compress_size} CRC32={info.CRC:08x}', flush=True)
        for name in args.member:
            info = archive.getinfo(name)
            target = LAB / 'downloads' / Path(name).name
            if target.exists():
                crc = 0
                with target.open('rb') as existing:
                    while block := existing.read(8 * 1024 * 1024):
                        crc = zlib.crc32(block, crc)
                if target.stat().st_size != info.file_size or crc != info.CRC:
                    raise RuntimeError(f'Existing file failed official member CRC/size: {target}')
                print(f'ALREADY_VERIFIED {target} CRC32={crc:08x}', flush=True)
                continue
            partial = target.with_suffix(target.suffix + '.partial')
            header = get_range(info.header_offset, info.header_offset + 29)
            fields = struct.unpack('<4s5H3I2H', header)
            if fields[0] != b'PK\x03\x04':
                raise RuntimeError('Invalid ZIP local header')
            data_start = info.header_offset + 30 + fields[-2] + fields[-1]
            parts = LAB / 'downloads' / ('.' + target.name + '.parts')
            parts.mkdir(exist_ok=True)
            spans = [(offset, min(offset + 16 * 1024 * 1024, info.compress_size))
                     for offset in range(0, info.compress_size, 16 * 1024 * 1024)]
            def fetch(span):
                start, end = span
                path = parts / f'{start:012d}.part'
                if not path.exists() or path.stat().st_size != end - start:
                    temporary = path.with_suffix('.tmp')
                    temporary.write_bytes(get_range(data_start + start, data_start + end - 1))
                    temporary.replace(path)
                return path
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                pending = {pool.submit(fetch, span) for span in spans}
                while pending:
                    done, pending = concurrent.futures.wait(pending, timeout=10,
                        return_when=concurrent.futures.FIRST_COMPLETED)
                    for future in done:
                        future.result()
                    received = sum(p.stat().st_size for p in parts.glob('*.part'))
                    print(f'DOWNLOAD {name} {received}/{info.compress_size} bytes ({received/info.compress_size:.1%})', flush=True)
            if info.compress_type != zipfile.ZIP_DEFLATED:
                raise RuntimeError('Expected ZIP_DEFLATED member')
            decoder = zlib.decompressobj(-15)
            checksum = 0
            with partial.open('wb') as dest:
                for start, end in spans:
                    block = decoder.decompress((parts / f'{start:012d}.part').read_bytes())
                    dest.write(block)
                    checksum = zlib.crc32(block, checksum)
                block = decoder.flush()
                dest.write(block)
                checksum = zlib.crc32(block, checksum)
            if checksum != info.CRC or partial.stat().st_size != info.file_size:
                raise RuntimeError('ZIP member size / CRC32 verification failed')
            partial.rename(target)
            print(f'VERIFIED {target} CRC32={checksum:08x}', flush=True)
            shutil.rmtree(parts)

if __name__ == '__main__':
    main()
