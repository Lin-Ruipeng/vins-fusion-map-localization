#!/usr/bin/env python3
"""Restore checksum-pinned public release assets without a GitHub account."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify(path, asset):
    if path.stat().st_size != asset['size_bytes'] or sha256(path) != asset['sha256']:
        raise RuntimeError('Asset size/SHA256 mismatch: %s. Keep the file for diagnosis, move it aside and retry.' % path)


def download(asset, base_url, root=ROOT):
    cache = root / 'artifacts/cache'
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / asset['name']
    if target.exists():
        verify(target, asset)
        print('VERIFIED_CACHE', target, flush=True)
        return target
    partial = target.with_name(target.name + '.partial')
    if partial.exists() and partial.stat().st_size == asset['size_bytes']:
        verify(partial, asset)
    else:
        url = base_url.rstrip('/') + '/' + asset['name']
        command = ['curl', '--fail', '--location', '--retry', '3', '--retry-delay', '2',
                   '--connect-timeout', '25', '--speed-limit', '1024', '--speed-time', '120',
                   '--max-time', '7200', '--continue-at', '-', '--output', str(partial), url]
        print('DOWNLOAD', asset['name'], '(public URL, no authentication)', flush=True)
        result = subprocess.run(command)
        if result.returncode:
            raise RuntimeError('Download interrupted (curl exit %d); partial retained at %s. Retry the same command.'
                               % (result.returncode, partial))
        verify(partial, asset)
    partial.rename(target)
    print('VERIFIED_DOWNLOAD', target, flush=True)
    return target


def install(source, asset, root=ROOT):
    target = root / asset['destination']
    if asset['kind'] != 'map':
        if target.exists():
            verify(target, asset)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(str(source), str(target))
        except OSError:
            shutil.copyfile(str(source), str(target))
        return
    if target.exists():
        # This is a reference-map restore, never an overwrite of a new map.
        check = target / 'SHA256SUMS'
        if not check.is_file():
            raise RuntimeError('Existing map has no checksum inventory: ' + str(target))
        subprocess.run(['sha256sum', '--quiet', '-c', 'SHA256SUMS'], cwd=str(target), check=True)
        return
    with tempfile.TemporaryDirectory(prefix='unpack-', dir=str(root / 'artifacts')) as temporary:
        temporary = Path(temporary)
        with tarfile.open(str(source), 'r:gz') as archive:
            for member in archive.getmembers():
                path = Path(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                    raise RuntimeError('Unsafe map archive entry: ' + member.name)
                if path.parts[:2] != ('maps', 'mh01'):
                    raise RuntimeError('Unexpected map archive entry: ' + member.name)
            archive.extractall(str(temporary))
        restored = temporary / 'maps/mh01'
        subprocess.run(['sha256sum', '--quiet', '-c', 'SHA256SUMS'], cwd=str(restored), check=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(restored), str(target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', nargs='?', choices=['image', 'map', 'bags', 'all'], default='map')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'artifacts/manifest.json').read_text())
    base = os.environ.get('ARTIFACT_BASE_URL', manifest['base_url'])
    for asset in manifest['assets']:
        if args.kind == 'all' or asset['kind'] == args.kind:
            install(download(asset, base), asset)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print('ARTIFACT_ERROR:', error, file=sys.stderr)
        sys.exit(2)
