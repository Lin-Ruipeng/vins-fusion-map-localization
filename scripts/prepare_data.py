#!/usr/bin/env python3
"""Extract selected EuRoC archives and check exact stereo/IMU timestamps."""
import argparse
import csv
import json
import statistics
import struct
import zipfile
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('sequence', choices=['MH_01_easy', 'MH_02_easy'])
parser.add_argument('--metadata-only', action='store_true')
args = parser.parse_args()
dest = LAB / 'data' / args.sequence
dest.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(LAB / 'downloads' / (args.sequence + '.zip')) as archive:
    for info in archive.infolist():
        if info.is_dir() or (args.metadata_only and not info.filename.endswith(('.csv', '.yaml', '.txt'))):
            continue
        archive.extract(info, dest)  # zipfile verifies each extracted member CRC.

def rows(path):
    with path.open(newline='') as f:
        return list(csv.reader(line for line in f if line.strip() and not line.startswith('#')))

root = dest / 'mav0'
summary = {'sequence': args.sequence, 'metadata_only': args.metadata_only}
all_stamps = {}
for sensor in ['cam0', 'cam1', 'imu0', 'state_groundtruth_estimate0']:
    records = rows(root / sensor / 'data.csv')
    stamps = [int(row[0]) for row in records]
    assert all(b > a for a, b in zip(stamps, stamps[1:])), sensor + ' non-monotonic timestamps'
    all_stamps[sensor] = stamps
    intervals = [b - a for a, b in zip(stamps, stamps[1:])]
    summary[sensor] = {'count': len(stamps), 'first_ns': stamps[0], 'last_ns': stamps[-1],
                       'median_interval_ns': statistics.median(intervals),
                       'min_interval_ns': min(intervals), 'max_interval_ns': max(intervals)}
    if sensor.startswith('cam') and not args.metadata_only:
        for row in records:
            path = root / sensor / 'data' / row[1].strip()
            with path.open('rb') as f:
                header = f.read(24)
            assert header[:8] == b'\x89PNG\r\n\x1a\n'
            assert struct.unpack('>II', header[16:24]) == (752, 480)
assert all_stamps['cam0'] == all_stamps['cam1'], 'Stereo timestamp mismatch'
for sensor in ['cam0', 'cam1', 'imu0']:
    assert (root / sensor / 'sensor.yaml').is_file(), 'Missing calibration ' + sensor
summary['stereo_timestamps_exactly_equal'] = True
summary['ground_truth_is_evaluation_only'] = True
(dest / 'validation.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
