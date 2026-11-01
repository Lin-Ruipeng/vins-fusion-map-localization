#!/usr/bin/env python
"""Export actual ROS message poses; compare live capture with the output bag."""
from __future__ import print_function
import csv
import json
import os
import re
import sys
import cv2
import numpy as np
import rosbag

run = '/work/results/' + sys.argv[1]
topics = {'/vins_estimator/odometry': 'vio', '/loop_fusion/odometry_rect': 'map'}
writers, files, poses = {}, [], {}
for topic, name in topics.items():
    f = open(run + '/' + name + '_from_bag.csv', 'wb')
    files.append(f)
    w = csv.writer(f)
    w.writerow(['timestamp_ns', 'bag_timestamp_ns', 'px', 'py', 'pz', 'qx', 'qy', 'qz', 'qw'])
    writers[topic], poses[topic] = w, {}
alignment = re.search(r'CROSS_SEQUENCE_ALIGN .*?stamp=(\S+)', open(run + '/loop.log').read())
alignment_stamp = float(alignment.group(1)) if alignment else None
saved_image = False
with rosbag.Bag(run + '/outputs.bag') as bag:
    for topic, msg, stamp in bag.read_messages(topics=list(topics) + ['/loop_fusion/match_image']):
        if topic == '/loop_fusion/match_image':
            if alignment_stamp and abs(msg.header.stamp.to_sec() - alignment_stamp) < 1e-5 and not saved_image:
                img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)
                img = img[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
                cv2.imwrite(run + '/first_cross_sequence_match.png', img)
                saved_image = True
            continue
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        ns = msg.header.stamp.to_nsec()
        values = [p.x, p.y, p.z, q.x, q.y, q.z, q.w]
        writers[topic].writerow([ns, stamp.to_nsec()] + values)
        poses[topic][ns] = values
for f in files:
    f.close()
summary = {'counts_from_bag': {k: len(v) for k, v in poses.items()},
           'first_alignment_match_image_exported': saved_image}
for topic, filename in [('/vins_estimator/odometry', 'vio_odometry.csv'),
                        ('/loop_fusion/odometry_rect', 'map_odometry.csv')]:
    with open(run + '/' + filename, 'rb') as f:
        live = list(csv.DictReader(f))
    maximum_error = 0.
    for row in live:
        ns = int(row['timestamp_ns'])
        values = [float(row[k]) for k in ['px', 'py', 'pz', 'qx', 'qy', 'qz', 'qw']]
        assert ns in poses[topic], 'Live message missing from bag'
        maximum_error = max(maximum_error, max(abs(a-b) for a,b in zip(values, poses[topic][ns])))
    assert len(live) == len(poses[topic]), 'Different live/bag pose counts'
    assert maximum_error < 1e-10, 'Live pose values differ from bag'
    summary[filename] = {'rows': len(live), 'max_live_bag_component_error': maximum_error}
    with open(run + '/' + topics[topic] + '.tum', 'w') as out:
        for row in live:
            out.write('%.9f %s\n' % (int(row['timestamp_ns']) / 1e9,
                ' '.join(row[k] for k in ['px', 'py', 'pz', 'qx', 'qy', 'qz', 'qw'])))
open(run + '/bag_export_validation.json', 'w').write(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
