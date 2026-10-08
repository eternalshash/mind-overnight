#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")"
mkdir -p out
export AUTH_ENABLED=false

./scripts/reset.sh
./scripts/start.sh

printf 'alice-pass\n' | ./scripts/create-account.sh Alice > out/alice.json
printf 'bob-pass-123\n' | ./scripts/create-account.sh Bob > out/bob.json
./scripts/grant-credits.sh Bob 100 > out/bob-grant.json

./scripts/list.sh Alice "Used textbook" 25 > out/listing.json
listing_id="$(jq -er ".listing_id" out/listing.json)"
./scripts/browse.sh > out/browse.json
./scripts/order.sh "$listing_id" Bob > out/order.json

jq -e '.status == "completed"' out/order.json >/dev/null

docker compose restart marketplace-service >/dev/null
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8080/listings >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
./scripts/order.sh "$listing_id" Bob > out/repeat.json
jq -e '.error == "listing is no longer available"' out/repeat.json >/dev/null

./scripts/stop.sh

echo "Starter baseline completed."
echo "Responses are saved in out/."
echo "The Project 2 account assembly and credit check remain TODOs."
echo "The services are stopped; the Postgres volume and signing keys are preserved."
