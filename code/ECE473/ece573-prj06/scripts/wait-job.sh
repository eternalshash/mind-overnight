#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <account_id> <job_id>" >&2
  exit 2
fi

headers=()
if [[ -n "${TOKEN:-}" ]]; then
  headers=(-H "Authorization: Bearer $TOKEN")
fi
response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT
account_id="$(jq -nr --arg id "$1" '$id | @uri')"
for attempt in $(seq 1 120); do
  code="$(curl -sS --max-time 5 -o "$response_file" -w '%{http_code}' \
    "${headers[@]}" \
    "http://127.0.0.1:8080/accounts/$account_id/jobs/$2" || true)"
  if [[ "$code" == 000 || "$code" == 404 || "$code" == 503 ]]; then
    sleep 1
    continue
  fi
  response="$(cat "$response_file")"
  if [[ "$code" != 200 && "$code" != 202 ]]; then
    echo "Job status returned HTTP $code: $response" >&2
    exit 1
  fi
  status="$(jq -r '.status' <<< "$response")"
  case "$status" in
    completed)
      jq -c '.result' <<< "$response"
      exit 0
      ;;
    rejected)
      jq -c '{error: .error_code, job_id: .job_id}' <<< "$response"
      exit 0
      ;;
    queued|processing)
      sleep 1
      ;;
    *)
      echo "Unexpected job status: $response" >&2
      exit 1
      ;;
  esac
done
echo "Timed out waiting for job $2" >&2
exit 1
