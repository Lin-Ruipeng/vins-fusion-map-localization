#!/usr/bin/env python3
"""Check the host boundary; ROS and scientific Python live in the container."""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIB = 1024 ** 3


def inspect(root):
    errors, warnings = [], []
    info = {'platform': platform.platform(), 'architecture': platform.machine(),
            'python': platform.python_version(), 'workspace': str(root)}
    if sys.version_info < (3, 8):
        errors.append('Host Python >=3.8 is required. Install python3 in Linux/WSL2.')
    if platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        errors.append('Supported runtime: Linux x86_64, including x86_64 WSL2. See docs/platforms.md.')
    missing = [c for c in ('git', 'curl', 'docker', 'gzip', 'tar', 'sha256sum', 'flock') if not shutil.which(c)]
    if missing:
        errors.append('Missing commands: ' + ', '.join(missing) + '. See docs/platforms.md.')
    try:
        with tempfile.TemporaryFile(dir=str(root)) as f:
            f.write(b'workspace-write-check')
    except OSError as error:
        errors.append('Workspace is not writable: ' + str(error))
    info['free_disk_gib'] = round(shutil.disk_usage(str(root)).free / GIB, 2)
    if info['free_disk_gib'] < 25:
        errors.append('Need at least 25 GiB free for a clean full run; 40 GiB is the recommended budget.')
    try:
        memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        info['host_memory_gib'] = round(int(memory['MemTotal'].split()[0]) * 1024 / GIB, 2)
        if info['host_memory_gib'] < 8:
            errors.append('At least 8 GiB visible memory is required; 16 GiB is recommended.')
    except (OSError, KeyError, ValueError):
        warnings.append('Could not determine memory; recommended host budget is 16 GiB.')
    if 'docker' not in missing:
        try:
            result = subprocess.run(['docker', 'info', '--format', '{{.Architecture}}'],
                                    capture_output=True, text=True, timeout=25)
            if result.returncode:
                errors.append('Docker daemon unavailable or permission denied: ' + result.stderr.strip()
                              + '\nSee docs/platforms.md; no host ROS installation is needed.')
            else:
                info['docker_architecture'] = result.stdout.strip()
                if info['docker_architecture'].lower() not in ('x86_64', 'amd64'):
                    errors.append('Docker daemon must run amd64 Linux containers.')
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append('Docker check failed: ' + str(error))
    info.update(status='failed' if errors else 'passed', errors=errors, warnings=warnings)
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    report = inspect(ROOT)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 2


if __name__ == '__main__':
    sys.exit(main())
