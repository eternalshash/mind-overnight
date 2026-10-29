#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <write: ONE|QUORUM|ALL> <read: ONE|QUORUM|ALL> <Cassandra nodes: 2|3>" >&2
  exit 2
fi

export WRITE_CONSISTENCY="${1^^}"
export READ_CONSISTENCY="${2^^}"
export CASSANDRA_NODES="$3"

for level in "$WRITE_CONSISTENCY" "$READ_CONSISTENCY"; do
  case "$level" in
    ONE|QUORUM|ALL) ;;
    *) echo "Invalid consistency: $level" >&2; exit 2 ;;
  esac
done
case "$CASSANDRA_NODES" in
  2|3) ;;
  *) echo "Cassandra nodes must be 2 or 3" >&2; exit 2 ;;
esac

cd "$(dirname "$0")"
export AUTH_ENABLED=false
mkdir -p out
result_file="out/experiment-write-${WRITE_CONSISTENCY,,}-read-${READ_CONSISTENCY,,}-nodes-${CASSANDRA_NODES}.txt"

./scripts/reset.sh
./scripts/start.sh

printf 'alice-pass\n' | ./scripts/create-account.sh Alice >/dev/null
printf 'bob-pass-123\n' | ./scripts/create-account.sh Bob >/dev/null
./scripts/grant-credits.sh Bob 100 >/dev/null

listing_ids=()
for i in $(seq 1 5); do
  listing_response="$(./scripts/list.sh Alice "Consistency item $i" 10)"
  listing_ids+=("$(jq -er '.listing_id' <<< "$listing_response")")
done

for listing_id in "${listing_ids[@]}"; do
  order_response="$(./scripts/order.sh "$listing_id" Bob)"
  jq -e '.status == "completed"' <<< "$order_response" >/dev/null
done

# Keep the HTTP status and formatted JSON body together, including HTTP 503.
headers_file="$(mktemp)"
body_file="$(mktemp)"
trap 'rm -f "$headers_file" "$body_file"' EXIT

curl -sS -D "$headers_file" -o "$body_file" \
  http://127.0.0.1:8080/accounts/Alice
{
  IFS= read -r status_line < "$headers_file"
  printf '%s\n\n' "${status_line%$'\r'}"
  jq . "$body_file"
} | tee "$result_file"

echo "Saved final query to $result_file"
echo "Services remain running for additional inspection; the next run resets them."
