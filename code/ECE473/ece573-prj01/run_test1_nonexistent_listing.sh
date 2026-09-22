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

# Test 1: Order from a listing that does not exist at all
scripts/order.sh listing-999 Bob > "$OUT_DIR/test1-order-nonexistent.json"

scripts/stop.sh

echo "Test 1 flow completed (ordering non-existent listing)."
echo "Responses are saved in $OUT_DIR."
