#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
mkdir -p "$LAB_ROOT/environment/home"
exec docker run --rm --init --user "$(id -u):$(id -g)" \
  --label "org.vins-fusion-lab.run=${VINS_RUN_ID:-manual}" \
  -e HOME=/work/environment/home -e ROS_HOME=/work/environment/home/.ros \
  -e ROS_MASTER_URI=http://127.0.0.1:11311 -e ROS_HOSTNAME=127.0.0.1 \
  -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 \
  -v "$LAB_ROOT:/work" -w /work --entrypoint /bin/bash \
  "${VINS_IMAGE:-vins-fusion-lab:kinetic-ceres1.14}" "$@"
