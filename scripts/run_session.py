#!/usr/bin/env python
"""Run the unmodified VIO/loop algorithms on sensor topics and record evidence.

Python 2.7 is intentional: this executes inside ROS Kinetic. Ground truth is
never published to either estimator. Container paths are stable under /work.
"""
from __future__ import print_function
import argparse
import csv
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import xmlrpclib

parser = argparse.ArgumentParser()
parser.add_argument('--sequence', choices=['MH_01_easy', 'MH_02_easy'], required=True)
parser.add_argument('--run', required=True)
parser.add_argument('--rate', type=float, default=0.5)
parser.add_argument('--load', action='store_true')
parser.add_argument('--save', action='store_true')
parser.add_argument('--duration', type=float)
parser.add_argument('--map-name', default='mh01')
args = parser.parse_args()
if args.rate <= 0:
    parser.error('rate must be positive')
if not re.match(r'^[A-Za-z0-9_-]+$', args.run):
    parser.error('run must be a simple directory name')
if not re.match(r'^[A-Za-z0-9_-]+$', args.map_name):
    parser.error('map-name must be a simple directory name')
run = '/work/results/' + args.run
if os.path.exists(run):
    raise RuntimeError('Refusing to overwrite an existing run: ' + run)
os.makedirs(run)
map_dir = '/work/maps/' + args.map_name + '/'
if not os.path.isdir(map_dir):
    os.makedirs(map_dir)
if args.load and not os.path.isfile(map_dir + 'pose_graph.txt'):
    raise RuntimeError('No saved map at ' + map_dir)
if args.save and os.path.exists(map_dir + 'pose_graph.txt'):
    raise RuntimeError('Refusing to overwrite the existing MH01 map')
calib_dir = '/work/src/VINS-Fusion/config/euroc/'
config = open(calib_dir + 'euroc_stereo_imu_config.yaml').read()
changes = {
    'output_path': '"' + run + '/"',
    'pose_graph_save_path': '"' + map_dir + '"',
    'load_previous_pose_graph': str(int(args.load)),
    'cam0_calib': '"' + calib_dir + 'cam0_mei.yaml"',
    'cam1_calib': '"' + calib_dir + 'cam1_mei.yaml"',
}
# Native VINS prepends the config directory to calibration names, even absolute
# names, so copy the two native calibration YAML files beside each run config.
import shutil
for camera in ['cam0', 'cam1']:
    filename = camera + '_mei.yaml'
    shutil.copyfile(calib_dir + filename, run + '/' + filename)
    changes[camera + '_calib'] = '"' + filename + '"'
for key, value in changes.items():
    config = re.sub(r'^' + key + r':.*$', key + ': ' + value, config, flags=re.M)
config_path = run + '/euroc_stereo_imu_config.yaml'
open(config_path, 'w').write(config)
open(run + '/invocation.json', 'w').write(json.dumps(vars(args), indent=2))
processes, logs, csv_files = [], [], []
counts, last_stamp, last_wall = {}, {}, {}
lock = threading.Lock()

def start(name, command, stdin=None):
    output = open(run + '/' + name + '.log', 'w')
    logs.append(output)
    p = subprocess.Popen(command, stdin=stdin, stdout=output, stderr=subprocess.STDOUT,
                         preexec_fn=os.setsid)
    processes.append((name, p))
    print('START', name, p.pid, ' '.join(command))
    return p

def stop(p, sig=signal.SIGINT, grace=10):
    if p.poll() is not None:
        return
    os.killpg(p.pid, sig)
    until = time.time() + grace
    while p.poll() is None and time.time() < until:
        time.sleep(0.1)
    if p.poll() is None:
        os.killpg(p.pid, signal.SIGTERM)
        time.sleep(0.5)
    if p.poll() is None:
        os.killpg(p.pid, signal.SIGKILL)
    p.wait()

def wait_master(required=False):
    master = xmlrpclib.ServerProxy('http://127.0.0.1:11311')
    deadline = time.time() + 90
    wanted = {'/imu0': ['/vins_estimator'],
              '/cam0/image_raw': ['/vins_estimator', '/loop_fusion'],
              '/cam1/image_raw': ['/vins_estimator'],
              '/vins_estimator/odometry': ['/loop_fusion']}
    while time.time() < deadline:
        try:
            code, _, state = master.getSystemState('/session_ready')
            subscribers = dict(state[1])
            if code == 1 and (not required or all(
                    node in subscribers.get(topic, [])
                    for topic, nodes in wanted.items() for node in nodes)):
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError('ROS nodes did not become ready')

summary = {'sequence': args.sequence, 'load_map': args.load,
           'replay_rate': args.rate, 'pose_frame': 'body/IMU',
           'ground_truth_used_for_estimation': False,
           'started_wall_s': time.time(), 'map_name': args.map_name}
def interrupted(signum, frame):
    raise KeyboardInterrupt('Signal %d' % signum)
signal.signal(signal.SIGINT, interrupted)
signal.signal(signal.SIGTERM, interrupted)
try:
    master = start('roscore', ['roscore'])
    wait_master()
    subprocess.check_call(['rosparam', 'set', '/use_sim_time', 'true'])
    import rospy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Image
    import cv2
    import numpy as np
    rospy.init_node('evidence_recorder', anonymous=False, disable_signals=True)
    def collect(topic, filename):
        f = open(run + '/' + filename, 'wb')
        csv_files.append(f)
        w = csv.writer(f)
        w.writerow(['timestamp_ns', 'receive_wall_s', 'px', 'py', 'pz', 'qx', 'qy', 'qz', 'qw'])
        counts[topic] = 0
        def callback(msg):
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            ns = msg.header.stamp.secs * 1000000000 + msg.header.stamp.nsecs
            now = time.time()
            with lock:
                w.writerow([ns, '%.9f' % now, p.x, p.y, p.z, q.x, q.y, q.z, q.w])
                f.flush()
                counts[topic] += 1
                last_stamp[topic] = ns
                last_wall[topic] = now
        return rospy.Subscriber(topic, Odometry, callback, queue_size=10000)
    subscriptions = [collect('/vins_estimator/odometry', 'vio_odometry.csv'),
                     collect('/loop_fusion/odometry_rect', 'map_odometry.csv')]
    image_count = [0]
    def match_image(msg):
        # Only a few samples are needed; all matches remain in the output bag.
        if image_count[0] < 12:
            image = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
            image = image[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
            cv2.imwrite(run + '/match_%03d.png' % image_count[0], image)
        image_count[0] += 1
    subscriptions.append(rospy.Subscriber('/loop_fusion/match_image', Image, match_image, queue_size=20))
    recorder = start('rosbag_record', ['rosbag', 'record', '--buffsize=256', '-O', run + '/outputs.bag',
        '/vins_estimator/odometry', '/loop_fusion/odometry_rect',
        '/vins_estimator/keyframe_pose', '/vins_estimator/extrinsic',
        '/loop_fusion/match_image', '/loop_fusion/pose_graph_path',
        '/loop_fusion/base_path', '/rosout', '/rosout_agg', '/clock'])
    vio = start('vins', ['stdbuf', '-oL', '-eL', '/work/catkin_ws/devel/lib/vins/vins_node', config_path])
    loop = start('loop', ['stdbuf', '-oL', '-eL', '/work/catkin_ws/devel/lib/loop_fusion/loop_fusion_node', config_path], stdin=subprocess.PIPE)
    wait_master(required=True)
    time.sleep(2)
    command = ['rosbag', 'play', '--clock', '--quiet', '-r', str(args.rate),
               '/work/data/' + args.sequence + '.bag']
    if args.duration:
        command.extend(['--duration', str(args.duration)])
    command.extend(['--topics', '/cam0/image_raw', '/cam1/image_raw', '/imu0'])
    player = start('replay', command)
    started, next_update = time.time(), time.time()
    while player.poll() is None:
        if vio.poll() is not None or loop.poll() is not None:
            raise RuntimeError('A VINS node exited during replay; inspect vins.log and loop.log')
        if time.time() >= next_update:
            with lock:
                print('PROGRESS wall_s=%.1f counts=%s last_stamp_ns=%s' % (
                    time.time() - started, json.dumps(counts), json.dumps(last_stamp)))
            next_update = time.time() + 10
        time.sleep(0.25)
    if player.returncode != 0:
        raise RuntimeError('rosbag play failed with code ' + str(player.returncode))
    # Let the native estimator queues, keyframe matching and optimizer drain.
    drained = time.time()
    while time.time() - drained < 120:
        if time.time() - drained > 12 and time.time() - max(list(last_wall.values()) or [drained]) > 8:
            break
        time.sleep(0.5)
    if not counts['/vins_estimator/odometry'] or not counts['/loop_fusion/odometry_rect']:
        raise RuntimeError('No actual VIO/corrected pose messages were recorded')
    if args.save:
        loop.stdin.write('s\n')
        loop.stdin.flush()
        until = time.time() + 90
        while loop.poll() is None and time.time() < until:
            time.sleep(0.2)
        if not os.path.isfile(map_dir + 'pose_graph.txt'):
            raise RuntimeError('The native save command did not produce a map')
        summary['save_node_returncode'] = loop.poll()
        summary['map_keyframes'] = sum(1 for _ in open(map_dir + 'pose_graph.txt'))
    summary['run_status'] = 'sensor_replay_and_pose_capture_complete'
    summary['elapsed_replay_wall_s'] = time.time() - started
    summary['counts'] = counts
    summary['last_timestamp_ns'] = last_stamp
    summary['match_images_published'] = image_count[0]
except BaseException as error:
    summary['run_status'] = 'failed'
    summary['error'] = repr(error)
    raise
finally:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    for name, p in reversed(processes):
        stop(p)
    for f in csv_files + logs:
        f.close()
    summary['process_exit_codes'] = {name: p.returncode for name, p in processes}
    open(run + '/session_summary.json', 'w').write(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
