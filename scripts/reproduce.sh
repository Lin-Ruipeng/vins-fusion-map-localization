#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if ! command -v python3 >/dev/null; then
  echo 'Python 3.8+ is required on the Linux/WSL2 host. See docs/platforms.md.' >&2
  exit 2
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 2)' || {
  echo 'Host Python must be >=3.8. Container ROS Python is supplied separately.' >&2
  exit 2
}
exec python3 -u "$LAB_ROOT/scripts/reproduce.py" "$@"
