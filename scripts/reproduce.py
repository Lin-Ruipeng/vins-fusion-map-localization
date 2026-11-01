#!/usr/bin/env python3
"""Full, fresh MH01-map -> MH02 localization run with auditable stage status."""
import argparse
import datetime
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def current_report(root, run, map_name, started):
    """Reference reports and another run's map cannot satisfy this run."""
    directory = root / 'results' / run
    report_path = directory / 'verification.json'
    invocation = json.loads((directory / 'invocation.json').read_text())
    report = json.loads(report_path.read_text())
    if (invocation.get('sequence') != 'MH_02_easy' or not invocation.get('load')
            or invocation.get('map_name') != map_name or not report.get('acceptance_passed')
            or report.get('first_alignment', {}).get('wall', 0) < started
            or report_path.stat().st_mtime < started):
        raise RuntimeError('Acceptance report does not prove this new MH02 run and new MH01 map')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', help='Optional unused run name; defaults to UTC timestamp + random suffix')
    parser.add_argument('--rate', type=float, default=float(os.environ.get('REPLAY_RATE', '0.5')))
    parser.add_argument('--timeout-minutes', type=float, default=120)
    args = parser.parse_args()
    if not 0 < args.rate <= 1:
        parser.error('rate must be >0 and <=1; use 0.25 for a slower CPU')
    if args.timeout_minutes <= 0:
        parser.error('timeout-minutes must be positive')
    run_id = args.run_id or datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + uuid.uuid4().hex[:6]
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        parser.error('run-id must contain only letters, numbers, underscore or dash')
    output = ROOT / 'results' / run_id
    if output.exists():
        parser.error('Run ID already exists; choose a new name. Existing results are preserved.')
    output.mkdir(parents=True)
    for directory in ('downloads', 'data', 'maps', 'src', 'logs', 'artifacts/cache', 'environment/home'):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    started = time.time()
    map_name, build_run, mh02_run = run_id + '_map', run_id + '_mh01', run_id + '_mh02'
    for path in (ROOT / 'maps' / map_name, ROOT / 'results' / build_run, ROOT / 'results' / mh02_run):
        if path.exists():
            parser.error('A stage name already exists: ' + str(path))
    status = {'status': 'running', 'run_id': run_id, 'started_at': utc_now(),
              'started_wall_s': started, 'mode': 'full', 'map_name': map_name,
              'mh01_run': build_run, 'mh02_run': mh02_run, 'stages': []}
    environment = os.environ.copy()
    environment.update(VINS_RUN_ID=run_id, MAP_NAME=map_name)
    active = [None]

    def save():
        path = output / 'summary.json'
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(status, indent=2) + '\n')
        temporary.replace(path)

    def interrupted(signum, frame):
        raise KeyboardInterrupt('Signal %d' % signum)

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)

    def stage(name, command):
        logfile = output / (name + '.log')
        record = {'name': name, 'command': command, 'log': str(logfile.relative_to(ROOT)),
                  'started_at': utc_now(), 'status': 'running'}
        status['stages'].append(record)
        status['current_stage'] = name
        save()
        before, next_update = time.time(), 0
        print('STAGE', name, 'log=' + record['log'], flush=True)
        with logfile.open('w') as log:
            process = subprocess.Popen(command, cwd=str(ROOT), env=environment,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            active[0] = process
            while process.poll() is None:
                if time.time() - started > args.timeout_minutes * 60:
                    raise RuntimeError('Overall timeout during ' + name + '; logs and download parts are retained')
                if time.time() >= next_update:
                    try:
                        with logfile.open('rb') as source:
                            source.seek(max(0, logfile.stat().st_size - 700))
                            tail = source.read().decode('utf-8', 'replace').strip().splitlines()
                        if tail:
                            print('PROGRESS', name, 'wall_s=%.1f' % (time.time() - before), tail[-1][-500:], flush=True)
                    except OSError:
                        pass
                    next_update = time.time() + 15
                time.sleep(.25)
        active[0] = None
        record.update(exit_code=process.returncode, elapsed_s=time.time()-before,
                      status='passed' if process.returncode == 0 else 'failed')
        save()
        if process.returncode:
            tail = logfile.read_text(errors='replace')[-3000:]
            raise RuntimeError('%s failed (exit %d). Inspect %s\n%s' % (name, process.returncode, logfile, tail))
        print('COMPLETE', name, 'wall_s=%.1f' % record['elapsed_s'], flush=True)

    try:
        save()
        stage('doctor', ['python3', 'scripts/doctor.py', '--json', str(output / 'doctor.json')])
        stage('environment_download', ['python3', 'scripts/download_artifacts.py', 'image'])
        stage('build', ['bash', 'scripts/build.sh'])
        stage('data', ['bash', 'scripts/download_data.sh'])
        stage('mh01_build', ['bash', 'scripts/run.sh', 'build-map', str(args.rate), build_run])
        stage('map_validate', ['python3', 'scripts/validate_map.py', map_name])
        stage('mh02_localization', ['bash', 'scripts/run.sh', 'mh02', str(args.rate), mh02_run])
        stage('export_verify', ['bash', 'scripts/export_and_verify.sh', mh02_run])
        report = current_report(ROOT, mh02_run, map_name, started)
        map_validation = json.loads((ROOT / 'maps' / map_name / 'validation.json').read_text())
        mh01_session = json.loads((ROOT / 'results' / build_run / 'session_summary.json').read_text())
        if (mh01_session['sequence'] != 'MH_01_easy' or mh01_session['load_map']
                or not mh01_session.get('map_keyframes')
                or any(code != 0 for code in mh01_session['process_exit_codes'].values())):
            raise RuntimeError('Fresh MH01 construction did not finish cleanly')
        status.update(status='passed', finished_at=utc_now(), elapsed_s=time.time()-started,
                      verification='results/' + mh02_run + '/verification.json',
                      map_keyframes=map_validation['keyframes'],
                      mh02_pose_pairs=report['corrected_pose_count'],
                      accepted_old_map_connections=report['accepted_connections_to_loaded_sequence'],
                      pose_frame='body/IMU', ground_truth_used_for_estimation=False)
    except BaseException as error:
        status.update(status='failed', error=str(error), finished_at=utc_now(), elapsed_s=time.time()-started)
        if status['stages'] and status['stages'][-1]['status'] == 'running':
            status['stages'][-1].update(status='failed', error=str(error))
        print('REPRODUCTION_FAILED:', error, file=sys.stderr, flush=True)
        print('Recovery: inspect this run summary/log, resolve the stated condition, then rerun with a NEW run ID. Verified downloads are reused.', file=sys.stderr)
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        # Only stop this invocation's containers; other users' ROS/Docker jobs are untouched.
        process = active[0]
        if process and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        try:
            containers = subprocess.run(['docker', 'ps', '-q', '--filter',
                'label=org.vins-fusion-lab.run=' + run_id], capture_output=True, text=True, timeout=20)
            containers.check_returncode()
            ids = containers.stdout.split()
            if ids:
                subprocess.run(['docker', 'stop', '--time', '20'] + ids, timeout=60, check=True)
        except (OSError, subprocess.SubprocessError) as error:
            status['cleanup_warning'] = str(error)
            if status['status'] == 'passed':
                status.update(status='failed', error='Could not confirm container cleanup')
        save()
    print('FULL_REPRODUCTION_' + status['status'].upper(), output / 'summary.json', flush=True)
    return 0 if status['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
