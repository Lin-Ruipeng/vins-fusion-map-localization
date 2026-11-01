#!/usr/bin/env python3
"""Validate every native pose-graph dependency before reusing the map."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent / 'maps' / (sys.argv[1] if len(sys.argv)>1 else 'mh01')
rows = [line.split() for line in (root / 'pose_graph.txt').read_text().splitlines() if line.strip()]
assert rows, 'Empty map'
indices = set()
for row in rows:
    assert len(row) == 26, 'Malformed pose graph row'
    index, count = int(row[0]), int(row[-1])
    assert index not in indices
    indices.add(index)
    for suffix in ['_keypoints.txt', '_briefdes.dat']:
        p = root / (str(index) + suffix)
        assert sum(1 for _ in p.open()) == count, 'Incomplete ' + str(p)
    p = root / (str(index) + '_image.png')
    assert p.stat().st_size > 1000, 'Missing saved image'
summary = {'keyframes': len(rows), 'keyframe_indices_min': min(indices),
           'keyframe_indices_max': max(indices), 'all_keypoint_descriptor_counts_match': True,
           'all_images_present': True,
           'pose_graph_sha256': hashlib.sha256((root / 'pose_graph.txt').read_bytes()).hexdigest()}
(root / 'validation.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
