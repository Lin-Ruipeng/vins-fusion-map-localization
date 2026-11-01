#!/usr/bin/env bash
set -euo pipefail
LAB_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$LAB_ROOT"
mkdir -p src logs environment/home
FROM_DOCKERFILE=0
if [[ "${1:-}" == --from-dockerfile ]]; then
  FROM_DOCKERFILE=1
elif [[ $# != 0 ]]; then
  echo 'Usage: build.sh [--from-dockerfile]' >&2
  exit 2
fi
REVISION=be55a937a57436548ddfb1bd324bc1e9a9e828e0
if [[ ! -d src/VINS-Fusion/.git ]]; then
  git clone https://github.com/HKUST-Aerial-Robotics/VINS-Fusion.git src/VINS-Fusion
  git -C src/VINS-Fusion checkout --detach "$REVISION"
fi
[[ $(git -C src/VINS-Fusion rev-parse HEAD) == "$REVISION" ]]
if git -C src/VINS-Fusion apply --reverse --check "$LAB_ROOT/patches/vins-fusion.patch" 2>/dev/null; then
  echo 'Validation/shutdown patch is already applied.'
else
  git -C src/VINS-Fusion apply --check "$LAB_ROOT/patches/vins-fusion.patch"
  git -C src/VINS-Fusion apply "$LAB_ROOT/patches/vins-fusion.patch"
fi
EXPECTED_IMAGE=$(python3 -c 'import json; print(json.load(open("artifacts/manifest.json"))["image_id"])')
ACTUAL_IMAGE=$(docker image inspect vins-fusion-lab:kinetic-ceres1.14 --format '{{.Id}}' 2>/dev/null || true)
if [[ "$FROM_DOCKERFILE" == 1 ]]; then
  docker build -t vins-fusion-lab:kinetic-ceres1.14 -f environment/Dockerfile environment
elif [[ "$ACTUAL_IMAGE" != "$EXPECTED_IMAGE" ]]; then
  python3 scripts/download_artifacts.py image
  gzip -dc environment/vins-fusion-lab-kinetic-ceres1.14.tar.gz | docker load
fi
ACTUAL_IMAGE=$(docker image inspect vins-fusion-lab:kinetic-ceres1.14 --format '{{.Id}}')
if [[ "$FROM_DOCKERFILE" != 1 && "$ACTUAL_IMAGE" != "$EXPECTED_IMAGE" ]]; then
  echo 'Locally rebuilt image differs from the released image. Restore the pinned release image with scripts/download_artifacts.sh image.' >&2
  exit 2
fi
bash scripts/container.sh /work/scripts/build_inside.sh
