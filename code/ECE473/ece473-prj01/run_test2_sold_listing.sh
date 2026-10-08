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

# Create an initial listing
scripts/list.sh Alice "Used textbook" 25 > "$OUT_DIR/test2-list.json"

# First buyer purchases the listing successfully
scripts/order.sh listing-1 Bob > "$OUT_DIR/test2-order-success.json"

# Test 2: Order from a listing that was sold already
scripts/order.sh listing-1 Charlie > "$OUT_DIR/test2-order-sold.json"

scripts/stop.sh

echo "Test 2 flow completed (ordering already-sold listing)."
echo "Responses are saved in $OUT_DIR."
