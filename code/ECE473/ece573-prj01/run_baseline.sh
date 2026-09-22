#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  echo "Example: $0" >&2
  exit 2
fi

cd "$(dirname "$0")"
OUT_DIR="out"

mkdir -p "$OUT_DIR"
scripts/build.sh
scripts/start.sh

scripts/list.sh Alice "Used textbook" 25 > "$OUT_DIR/baseline-list.json"
scripts/browse.sh > "$OUT_DIR/baseline-browse.json"
scripts/order.sh listing-1 Bob > "$OUT_DIR/baseline-order.json"

scripts/stop.sh

echo "Baseline flow completed."
echo "Responses are saved in $OUT_DIR."
