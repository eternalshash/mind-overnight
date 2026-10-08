#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
docker compose down --volumes

echo "Services stopped and Project 2 database state removed."

