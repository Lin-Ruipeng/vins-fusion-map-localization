#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/kinetic/setup.bash
mkdir -p /work/catkin_ws/src
ln -sfn /work/src/VINS-Fusion /work/catkin_ws/src/VINS-Fusion
cd /work/catkin_ws
catkin_make -j3 -l3 -DCMAKE_BUILD_TYPE=Release \
  '-DCATKIN_WHITELIST_PACKAGES=camera_models;vins;loop_fusion'
