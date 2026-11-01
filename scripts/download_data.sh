#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$LAB_ROOT"
mkdir -p downloads data
exec 9>data/.preparation.lock
flock -n 9 || { echo 'Another data preparation is running; wait for it, then retry.' >&2; exit 2; }
# EUROC_SOURCE=mirror selects the byte-identical public Hugging Face mirror.
# Both sources are checked against the official ETH ZIP member CRC values.
python3 scripts/fetch_euroc.py --workers "${DOWNLOAD_WORKERS:-6}" \
  --member machine_hall/MH_02_easy/MH_02_easy.zip \
  --member machine_hall/MH_01_easy/MH_01_easy.zip
for SEQUENCE in MH_01_easy MH_02_easy; do
  if [[ "$SEQUENCE" == MH_01_easy && -f data/MH_01_easy.bag ]]; then
    python3 scripts/prepare_data.py "$SEQUENCE" --metadata-only
  else
    python3 scripts/prepare_data.py "$SEQUENCE"
  fi
  if [[ ! -f "data/$SEQUENCE.bag" ]]; then
    bash scripts/container.sh -c \
      'source /opt/ros/kinetic/setup.bash; exec python -u /work/scripts/asl_to_bag.py "$1"' _ "$SEQUENCE"
  fi
  bash scripts/container.sh -c \
    'source /opt/ros/kinetic/setup.bash; exec python -u /work/scripts/validate_input_bag.py "$1"' _ "$SEQUENCE"
done
