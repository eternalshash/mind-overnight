#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  echo "Example: $0" >&2
  exit 2
fi

docker rm -f ece573-prj01
