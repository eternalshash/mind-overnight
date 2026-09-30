#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")"
mkdir -p out

check_contains() {
  local file="$1"
  local expected="$2"
  local description="$3"

  if ! grep -Fq "$expected" "$file"; then
    echo "Acceptance check failed: $description" >&2
    echo "Expected to find: $expected" >&2
    echo "Inspect $file and the service logs for details." >&2
    exit 1
  fi
}

./scripts/reset.sh
./scripts/start.sh

./scripts/create-account.sh Alice 100 > out/seller-account.json
./scripts/create-account.sh Bob 100 > out/buyer-before.json
./scripts/create-account.sh Carol 10 > out/low-credit-before.json
./scripts/list.sh Alice "Used textbook" 25 > out/listing.json
listing_id="$(jq -er ".listing_id" out/listing.json)"
./scripts/browse.sh Alice > out/seller-listings.json
./scripts/order.sh "$listing_id" Bob > out/order.json
order_id="$(jq -er ".order_id" out/order.json)"
./scripts/account.sh Bob > out/buyer-after.json
./scripts/account.sh Alice > out/seller-after.json

check_contains out/seller-account.json '"balance":100' "Alice starts with 100 credits"
check_contains out/buyer-before.json '"balance":100' "Bob starts with 100 credits"
check_contains out/buyer-after.json '"balance":75' "checkout debits Bob by 25 credits"
check_contains out/seller-after.json '"balance":125' "checkout credits Alice by 25 credits"
check_contains out/order.json '"status":"completed"' "checkout creates a completed order"
check_contains out/seller-listings.json "\"listing_id\":\"$listing_id\"" "seller-filtered browse returns Alice's listing"
check_contains out/buyer-after.json "\"orders\":[{\"order_id\":\"$order_id\"" "Bob's account includes the order"
check_contains out/seller-after.json "\"sales\":[{\"order_id\":\"$order_id\"" "Alice's account includes the sale"

./scripts/list.sh Alice "Laptop" 50 > out/expensive-listing.json
expensive_listing_id="$(jq -er ".listing_id" out/expensive-listing.json)"
./scripts/order.sh "$expensive_listing_id" Carol > out/insufficient-credit.json
./scripts/account.sh Carol > out/low-credit-after.json
./scripts/browse.sh Alice > out/seller-available-after.json

check_contains out/insufficient-credit.json 'buyer has insufficient credit' "Carol's insufficient-credit order is rejected"
check_contains out/low-credit-after.json '"balance":10' "a rejected order leaves Carol's balance unchanged"
check_contains out/seller-available-after.json "\"listing_id\":\"$expensive_listing_id\"" "a rejected order leaves the listing available"

./scripts/order.sh "$listing_id" Bob > out/repeat-order.json
./scripts/account.sh Bob > out/buyer-after-repeat.json

check_contains out/repeat-order.json 'listing is no longer available' "a sold listing cannot be ordered again"
check_contains out/buyer-after-repeat.json '"balance":75' "a repeated order does not debit Bob again"

./scripts/reset.sh

echo "Project 2 acceptance test passed."
echo "Responses are saved in out/."
echo "Services are stopped and Project 2 database state is removed."
