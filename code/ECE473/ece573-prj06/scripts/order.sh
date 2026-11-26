#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <listing_id> <buyer_id>" >&2
  echo "Example: $0 listing-1 Bob" >&2
  exit 2
fi

headers=()
if [[ -n "${TOKEN:-}" ]]; then
  headers=(-H "Authorization: Bearer $TOKEN")
fi

payload="$(jq -nc --arg listing "$1" --arg buyer "$2" \
  '{listing_id: $listing, buyer_id: $buyer}')"
response="$(curl -sS "${headers[@]}" -X POST http://127.0.0.1:8080/orders \
  -H 'Content-Type: application/json' --data "$payload")"
if ! job_id="$(jq -er '.job_id' <<< "$response")"; then
  printf '%s\n' "$response"
  exit 0
fi
"$(dirname "$0")/wait-job.sh" "$2" "$job_id"
