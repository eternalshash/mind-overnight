#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <seller_id> <title> <credit_cost>" >&2
  echo "Example: $0 Alice 'Used textbook' 25" >&2
  exit 2
fi

headers=()
if [[ -n "${TOKEN:-}" ]]; then
  headers=(-H "Authorization: Bearer $TOKEN")
fi

payload="$(jq -nc --arg seller "$1" --arg title "$2" --argjson cost "$3" \
  '{seller_id: $seller, title: $title, credit_cost: $cost}')"
response="$(curl -sS "${headers[@]}" -X POST http://127.0.0.1:8080/listings \
  -H 'Content-Type: application/json' --data "$payload")"
if ! job_id="$(jq -er '.job_id' <<< "$response")"; then
  printf '%s\n' "$response"
  exit 0
fi
"$(dirname "$0")/wait-job.sh" "$1" "$job_id"
