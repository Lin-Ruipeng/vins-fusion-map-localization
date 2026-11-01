#!/usr/bin/env python
"""Convert EuRoC ASL sensor data to ROS1 with integer nanosecond timestamps.

Ground truth is intentionally excluded from the bag used by the estimators.
"""
from __future__ import print_function
import csv
import heapq
import os
import sys
import time
import cv2
import rosbag
import rospy
from sensor_msgs.msg import Image, Imu

sequence = sys.argv[1]
root = '/work/data/' + sequence + '/mav0'
target = '/work/data/' + sequence + '.bag'
if os.path.exists(target):
    raise RuntimeError('Refusing to overwrite ' + target)
def records(sensor, order):
    with open(root + '/' + sensor + '/data.csv', 'rb') as f:
        for row in csv.reader(line for line in f if line.strip() and not line.startswith('#')):
            yield int(row[0]), order, sensor, row
counts = {'cam0': 0, 'cam1': 0, 'imu0': 0}
started = time.time()
with rosbag.Bag(target + '.partial', 'w') as bag:
    for ns, _, sensor, row in heapq.merge(records('cam0', 0), records('cam1', 1), records('imu0', 2)):
        sec, nsec = divmod(ns, 1000000000)
        stamp = rospy.Time(sec, nsec)
        if sensor == 'imu0':
            msg = Imu()
            values = list(map(float, row[1:7]))
            msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = values[:3]
            msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = values[3:]
            msg.orientation_covariance[0] = -1
            topic = '/imu0'
        else:
            image = cv2.imread(root + '/' + sensor + '/data/' + row[1].strip(), 0)
            if image is None or image.shape != (480, 752):
                raise RuntimeError('Image decode failed: ' + str(row))
            msg = Image()
            msg.height, msg.width = image.shape
            msg.encoding, msg.is_bigendian, msg.step = 'mono8', 0, image.shape[1]
            msg.data = image.tostring()
            topic = '/' + sensor + '/image_raw'
        msg.header.stamp, msg.header.frame_id, msg.header.seq = stamp, sensor, counts[sensor]
        bag.write(topic, msg, stamp)
        counts[sensor] += 1
        if sum(counts.values()) % 5000 == 0:
            print('CONVERT', counts, 'wall_s', time.time() - started)
os.rename(target + '.partial', target)
print('DONE', target, counts, 'wall_s', time.time() - started)
