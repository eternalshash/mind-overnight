#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <account_id> <starting_balance>" >&2
  echo "Example: $0 Dave 100" >&2
  exit 2
fi

curl -sS -X POST http://127.0.0.1:8080/accounts \
  -H 'Content-Type: application/json' \
  --data "{\"account_id\":\"$1\",\"starting_balance\":$2}"
printf '\n'
