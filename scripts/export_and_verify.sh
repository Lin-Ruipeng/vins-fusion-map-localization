#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RUN=${1:-mh02_localization}
exec bash "$LAB_ROOT/scripts/container.sh" -c \
  'source /opt/ros/kinetic/setup.bash; python -u /work/scripts/export_results.py "$1" && python -u /work/scripts/analyze.py "$1"' _ "$RUN"
