#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")"
mkdir -p out

export AUTH_ENABLED=false
export READ_CONSISTENCY=QUORUM
export WRITE_CONSISTENCY=QUORUM

# Start from fresh project volumes.
./scripts/reset.sh
./scripts/start.sh

# Create the accounts and an available listing.
printf 'alice-pass\n' | ./scripts/create-account.sh Alice > out/alice.json
printf 'bob-pass-123\n' | ./scripts/create-account.sh Bob > out/bob.json
./scripts/grant-credits.sh Bob 100 > out/bob-grant.json

./scripts/list.sh Alice "Used textbook" 25 > out/listing.json
listing_id="$(jq -er '.listing_id' out/listing.json)"

./scripts/browse.sh > out/browse.json
jq -e --arg listing_id "$listing_id" \
  '[.listings[].listing_id] | index($listing_id) != null' \
  out/browse.json >/dev/null

./scripts/order.sh "$listing_id" Bob > out/order.json
jq -e '.status == "completed"' out/order.json >/dev/null
order_id="$(jq -er '.order_id' out/order.json)"
day="$(jq -er '.ordered_at | split("T")[0]' out/order.json)"

# Restart marketplace and verify the sold listing cannot be ordered again.
docker compose restart marketplace-service >/dev/null
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8080/listings >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

./scripts/order.sh "$listing_id" Bob > out/repeat.json
jq -e '.error == "listing is no longer available"' out/repeat.json >/dev/null

# Check balances, matching order IDs, and the sold listing's status.
./scripts/account.sh Bob > out/bob-account.json
./scripts/account.sh Alice > out/alice-account.json
./scripts/browse.sh > out/browse-after-order.json

jq -e --arg order_id "$order_id" \
  '.balance == 75 and (.orders | length) == 1 and
   .orders[0].order_id == $order_id and (.sales | length) == 0' \
  out/bob-account.json >/dev/null
jq -e --arg order_id "$order_id" --arg listing_id "$listing_id" \
  '.balance == 25 and (.sales | length) == 1 and
   .sales[0].order_id == $order_id and (.listings | length) == 1 and
   .listings[0].listing_id == $listing_id and .listings[0].status == "sold"' \
  out/alice-account.json >/dev/null
jq -e --arg listing_id "$listing_id" \
  '(.listings | type) == "array" and all(.listings[]; .listing_id != $listing_id)' \
  out/browse-after-order.json >/dev/null

# The order appears on its UTC day, but not in an earlier date range.
./scripts/account.sh Bob "$day" "$day" > out/bob-day.json
jq -e --arg order_id "$order_id" \
  '(.orders | length) == 1 and .orders[0].order_id == $order_id' \
  out/bob-day.json >/dev/null

./scripts/account.sh Bob 2000-01-01 2000-01-02 > out/bob-empty-range.json
jq -e '.balance == 75 and (.orders | length) == 0' \
  out/bob-empty-range.json >/dev/null

./scripts/stop.sh

echo "Starter baseline completed."
echo "Responses are saved in out/."
echo "Cassandra account and listing views were checked after marketplace restart."
echo "The services are stopped; the Postgres volume and signing keys are preserved."
