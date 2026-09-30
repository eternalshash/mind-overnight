#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")"
mkdir -p out

./scripts/reset.sh
./scripts/start.sh

./scripts/create-account.sh Alice 100 > out/alice-account.json
./scripts/create-account.sh Bob 100 > out/bob-account.json

./scripts/list.sh Alice "Used textbook" 25 > out/listing.json
listing_id="$(jq -er ".listing_id" out/listing.json)"
./scripts/browse.sh Alice > out/alice-listings.json
./scripts/order.sh "$listing_id" Bob > out/order.json

grep -q '"status":"completed"' out/order.json
grep -q "\"listing_id\":\"$listing_id\"" out/alice-listings.json

docker compose restart marketplace-service >/dev/null
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8080/listings >/dev/null; then
    break
  fi
  sleep 1
done
./scripts/order.sh "$listing_id" Bob > out/repeat-after-restart.json
grep -q 'listing is no longer available' out/repeat-after-restart.json

./scripts/stop.sh

echo "Starter baseline completed."
echo "Responses are saved in out/."
echo "The insufficient-credit check and account response remain Project 2 TODOs."
echo "The services are stopped and the Postgres volume is preserved."

