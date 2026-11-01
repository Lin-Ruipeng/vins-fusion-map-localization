#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
MODE=${1:?Usage: run.sh build-map|mh01-check|mh02 [rate] [run-name]}
RATE=${2:-0.5}
RUN=${3:-${MODE}_$(date +%Y%m%d_%H%M%S)}
DURATION=${4:-}
case "$MODE" in
  build-map) SEQUENCE=MH_01_easy; EXTRA=(--save) ;;
  mh01-check) SEQUENCE=MH_01_easy; EXTRA=(--load) ;;
  mh02) SEQUENCE=MH_02_easy; EXTRA=(--load) ;;
  *) echo "Unknown mode: $MODE" >&2; exit 2 ;;
esac
if [[ -n "$DURATION" ]]; then EXTRA+=(--duration "$DURATION"); fi
exec bash "$LAB_ROOT/scripts/container.sh" -c \
  'source /opt/ros/kinetic/setup.bash; source /work/catkin_ws/devel/setup.bash; exec python -u /work/scripts/run_session.py "$@"' \
  _ --sequence "$SEQUENCE" --run "$RUN" --rate "$RATE" --map-name "${MAP_NAME:-mh01}" "${EXTRA[@]}"
