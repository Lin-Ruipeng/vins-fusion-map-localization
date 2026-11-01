#!/usr/bin/env python
"""Regression: native save and SIGINT must terminate without SIGABRT or a hang."""
from __future__ import print_function
import json
import os
import re
import signal
import subprocess
import sys
import time
import xmlrpclib

root = '/work/results/' + sys.argv[1]
os.makedirs(root)
os.mkdir(root + '/map')
source = '/work/src/VINS-Fusion/config/euroc/'
config = open(source + 'euroc_stereo_imu_config.yaml').read()
import shutil
for name in ['cam0_mei.yaml', 'cam1_mei.yaml']:
    shutil.copyfile(source + name, root + '/' + name)
for key, value in {'output_path': '"' + root + '/"',
                   'pose_graph_save_path': '"' + root + '/map/"',
                   'load_previous_pose_graph': '0'}.items():
    config = re.sub(r'^' + key + r':.*$', key + ': ' + value, config, flags=re.M)
open(root + '/config.yaml', 'w').write(config)
logs, processes = [], []
def start(name, command, stdin=None):
    f = open(root + '/' + name + '.log', 'w')
    logs.append(f)
    p = subprocess.Popen(command, stdin=stdin, stdout=f, stderr=subprocess.STDOUT, preexec_fn=os.setsid)
    processes.append(p)
    return p
def wait(p, timeout):
    end = time.time() + timeout
    while p.poll() is None and time.time() < end:
        time.sleep(.1)
    return p.poll()
try:
    master = start('roscore', ['roscore'])
    server = xmlrpclib.ServerProxy('http://127.0.0.1:11311')
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if server.getPid('/shutdown_probe')[0] == 1:
                break
        except Exception:
            pass
        time.sleep(.1)
    vio = start('vins', ['/work/catkin_ws/devel/lib/vins/vins_node', root + '/config.yaml'])
    loop = start('loop', ['stdbuf', '-oL', '/work/catkin_ws/devel/lib/loop_fusion/loop_fusion_node', root + '/config.yaml'], subprocess.PIPE)
    deadline = time.time() + 30
    while time.time() < deadline:
        subscriptions = dict(server.getSystemState('/shutdown_probe')[2][1])
        if '/loop_fusion' in subscriptions.get('/vins_estimator/odometry', []):
            break
        time.sleep(.1)
    else:
        raise RuntimeError('Nodes not ready')
    loop.stdin.write('s\n')
    loop.stdin.flush()
    os.killpg(vio.pid, signal.SIGINT)
    codes = {'loop_native_save': wait(loop, 8), 'vio_sigint': wait(vio, 8)}
    print(json.dumps(codes))
    open(root + '/verdict.json', 'w').write(json.dumps(codes, indent=2))
    assert all(code == 0 for code in codes.values()), 'Shutdown regression: ' + str(codes)
finally:
    for p in reversed(processes):
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGINT)
            if wait(p, 4) is None:
                os.killpg(p.pid, signal.SIGKILL)
            p.wait()
    for f in logs:
        f.close()
