#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  echo "Example: $0" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
docker build -t ece573-prj01 marketplace-service

echo "Image built. Run ./scripts/start.sh to use the new image."
