#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <account_id>" >&2
  echo "Example: $0 Bob" >&2
  exit 2
fi

headers=()
if [[ -n "${TOKEN:-}" ]]; then
  headers=(-H "Authorization: Bearer $TOKEN")
fi

curl -sS "${headers[@]}" "http://127.0.0.1:8080/accounts/$1"
printf '\n'
