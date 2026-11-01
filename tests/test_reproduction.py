"""Host-side regression tests for real onboarding failure boundaries."""
import contextlib
import hashlib
import http.server
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import doctor
import download_artifacts as assets
import fetch_euroc
import reproduce


class Handler(http.server.BaseHTTPRequestHandler):
    data = b'vins-reproduction-fixture-' * 4000
    drop = False
    requests = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        type(self).requests.append(dict(self.headers))
        if self.path.startswith('/fail/'):
            self.send_response(429)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        span = self.headers.get('Range', 'bytes=0-')[len('bytes='):]
        start, end = span.split('-')
        start, end = int(start), int(end) if end else len(self.data)-1
        code = 206 if self.headers.get('Range') else 200
        self.send_response(code)
        if code == 206:
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, len(self.data)))
        self.send_header('Content-Length', str(end-start+1))
        self.end_headers()
        if type(self).drop:
            type(self).drop = False
            self.wfile.write(self.data[start:start+8192])
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            return
        self.wfile.write(self.data[start:end+1])


@contextlib.contextmanager
def server():
    Handler.requests, Handler.drop = [], False
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    try:
        yield 'http://127.0.0.1:%d' % httpd.server_port
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join()


def asset():
    return {'name': 'fixture.bin', 'kind': 'image', 'destination': 'environment/fixture.bin',
            'size_bytes': len(Handler.data), 'sha256': hashlib.sha256(Handler.data).hexdigest()}


class ReproductionTests(unittest.TestCase):
    def test_missing_docker_is_actionable(self):
        real = doctor.shutil.which
        with tempfile.TemporaryDirectory() as directory, patch.object(doctor.shutil, 'which',
                side_effect=lambda name: None if name == 'docker' else real(name)):
            result = doctor.inspect(Path(directory))
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(any('docker' in error and 'docs/platforms.md' in error for error in result['errors']))

    def test_docker_permission_error_is_preserved(self):
        result = subprocess.CompletedProcess(['docker'], 1, '', 'permission denied at docker.sock')
        with tempfile.TemporaryDirectory() as directory, patch.object(doctor.shutil, 'which', return_value='/usr/bin/tool'), patch.object(doctor.subprocess, 'run', return_value=result):
            report = doctor.inspect(Path(directory))
        self.assertTrue(any('permission denied at docker.sock' in error for error in report['errors']))

    def test_interrupted_public_download_resumes_and_verifies(self):
        with tempfile.TemporaryDirectory() as directory, server() as base:
            root = Path(directory)
            Handler.drop = True
            with self.assertRaisesRegex(RuntimeError, 'partial retained'):
                assets.download(asset(), base, root)
            partial = root / 'artifacts/cache/fixture.bin.partial'
            self.assertGreater(partial.stat().st_size, 0)
            final = assets.download(asset(), base, root)
            self.assertEqual(final.read_bytes(), Handler.data)
            self.assertTrue(any(r.get('Range', '').startswith('bytes=8192-') for r in Handler.requests))
            self.assertTrue(all('Authorization' not in r for r in Handler.requests))

    def test_corrupt_asset_is_not_installed(self):
        with tempfile.TemporaryDirectory() as directory, server() as base:
            root = Path(directory)
            metadata = asset()
            metadata['sha256'] = '0' * 64
            with self.assertRaisesRegex(RuntimeError, 'SHA256 mismatch'):
                source = assets.download(metadata, base, root)
                assets.install(source, metadata, root)
            self.assertFalse((root / metadata['destination']).exists())

    def test_euroc_range_falls_back_after_429(self):
        with server() as base, patch.object(fetch_euroc, 'SOURCES', [base+'/fail/file', base+'/good/file']), patch.object(fetch_euroc, 'SIZE', len(Handler.data)), patch.object(fetch_euroc.time, 'sleep'):
            self.assertEqual(fetch_euroc.get_range(100, 500), Handler.data[100:501])
            self.assertEqual(len(Handler.requests), 2)

    def test_old_report_cannot_pass_new_reproduction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / 'results/new_mh02'
            run.mkdir(parents=True)
            (run/'invocation.json').write_text(json.dumps({'sequence': 'MH_02_easy', 'load': True, 'map_name': 'new_map'}))
            (run/'verification.json').write_text(json.dumps({'acceptance_passed': True, 'first_alignment': {'wall': time.time()-100}}))
            with self.assertRaisesRegex(RuntimeError, 'this new MH02 run'):
                reproduce.current_report(root, 'new_mh02', 'new_map', time.time())

    def test_existing_map_from_another_run_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root/'maps/mh01'
            target.mkdir(parents=True)
            (target/'pose_graph.txt').write_text('my new map')
            metadata = {'kind': 'map', 'destination': 'maps/mh01', 'pose_graph_sha256': '0'*64}
            with self.assertRaisesRegex(RuntimeError, 'another run'):
                assets.install(root/'unused.tar.gz', metadata, root)
            self.assertEqual((target/'pose_graph.txt').read_text(), 'my new map')

    def test_duplicate_run_is_rejected_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root/'results/already_used'
            existing.mkdir(parents=True)
            sentinel = existing/'summary.json'
            sentinel.write_text('original result')
            with patch.object(reproduce, 'ROOT', root), patch.object(sys, 'argv', ['reproduce.py', '--run-id', 'already_used']):
                with self.assertRaises(SystemExit) as error:
                    reproduce.main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(sentinel.read_text(), 'original result')


if __name__ == '__main__':
    unittest.main()
