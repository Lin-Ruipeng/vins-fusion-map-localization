#!/usr/bin/env python
"""Validate every sensor timestamp against ASL CSV; GT topics are never replayed."""
from __future__ import print_function
import csv
import json
import sys
import rosbag

sequence = sys.argv[1]
root = '/work/data/' + sequence + '/mav0/'
topics = {'/cam0/image_raw': 'cam0', '/cam1/image_raw': 'cam1', '/imu0': 'imu0'}
expected, counts = {}, {}
for topic, sensor in topics.items():
    with open(root + sensor + '/data.csv', 'rb') as source:
        expected[topic] = [int(row[0]) for row in csv.reader(
            line for line in source if line.strip() and not line.startswith('#'))]
    counts[topic] = 0
with rosbag.Bag('/work/data/' + sequence + '.bag') as bag:
    for topic, msg, stamp in bag.read_messages(topics=list(topics)):
        index = counts[topic]
        assert index < len(expected[topic]), 'Too many messages: ' + topic
        assert msg.header.stamp.to_nsec() == expected[topic][index], 'Timestamp differs from ASL CSV: ' + topic
        if topic != '/imu0':
            assert (msg.width, msg.height) == (752, 480), 'Wrong image dimensions'
            assert msg.encoding in ('mono8', '8UC1'), 'Wrong grayscale encoding'
        counts[topic] += 1
for topic in topics:
    assert counts[topic] == len(expected[topic]), 'Incomplete bag: ' + topic
summary = {'sequence': sequence, 'counts': counts,
           'all_sensor_header_timestamps_match_asl_csv': True,
           'replayed_topics': sorted(topics), 'ground_truth_replayed': False}
open('/work/data/' + sequence + '.bag.validation.json', 'w').write(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
