#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")"
mkdir -p out/attack
export AUTH_ENABLED=true

post() {
  local url="$1"
  local body="$2"
  local token="$3"
  local file="$4"

  curl -sS -o "$file" -w '%{http_code}' -X POST "$url" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $token" \
    --data "$body"
}

expect() {
  if [[ "$1" != "$2" ]]; then
    echo "Expected HTTP $2, got $1. Inspect $3 and docker compose logs." >&2
    exit 1
  fi
}

./scripts/reset.sh
./scripts/start.sh

admin_token="$(./scripts/admin-login.sh | jq -er .access_token)"

printf 'alice-pass\n' | ./scripts/create-account.sh Alice > out/attack/alice-registration.json
jq -e '.balance == 0' out/attack/alice-registration.json >/dev/null

alice_token="$(printf 'alice-pass\n' | ./scripts/login.sh Alice | jq -er .access_token)"

printf 'bob-pass-123\n' | ./scripts/create-account.sh Bob > out/attack/bob-registration.json
jq -e '.balance == 0' out/attack/bob-registration.json >/dev/null
bob_token="$(printf 'bob-pass-123\n' | ./scripts/login.sh Bob | jq -er .access_token)"

# Test 1: A wrong password cannot log in (401).
status="$(curl -sS -o out/attack/wrong-password.json -w '%{http_code}' \
  -X POST http://127.0.0.1:8081/login \
  -H 'Content-Type: application/json' \
  --data '{"account_id":"Alice","password":"wrong-pass"}')"
expect "$status" 401 out/attack/wrong-password.json
jq -e '.error == "invalid account or password" and (has("access_token") | not)' out/attack/wrong-password.json >/dev/null

grant='{"amount":100}'
# Test 2: A regular user cannot grant credits (403).
status="$(post http://127.0.0.1:8080/accounts/Bob/credits "$grant" "$alice_token" out/attack/nonadmin-grant.json)"
expect "$status" 403 out/attack/nonadmin-grant.json

# Test 3: Admin cannot grant credits to an admin account (400).
status="$(post http://127.0.0.1:8080/accounts/course-admin/credits "$grant" "$admin_token" out/attack/admin-grant.json)"
expect "$status" 400 out/attack/admin-grant.json

listing='{"seller_id":"Alice","title":"Used textbook","credit_cost":25}'
# Test 4: A missing token cannot create a listing (401).
status="$(post http://127.0.0.1:8080/listings "$listing" "" out/attack/missing-token.json)"
expect "$status" 401 out/attack/missing-token.json

# Test 5: An invalid token cannot create a listing (401).
status="$(post http://127.0.0.1:8080/listings "$listing" "not-a-token" out/attack/invalid-token.json)"
expect "$status" 401 out/attack/invalid-token.json

# Test 6: Bob cannot create a listing for Alice (403).
status="$(post http://127.0.0.1:8080/listings "$listing" "$bob_token" out/attack/identity-attack.json)"
expect "$status" 403 out/attack/identity-attack.json

admin_listing='{"seller_id":"course-admin","title":"Admin item","credit_cost":25}'
# Test 7: Admin cannot create a listing (403).
status="$(post http://127.0.0.1:8080/listings "$admin_listing" "$admin_token" out/attack/admin-listing.json)"
expect "$status" 403 out/attack/admin-listing.json

order='{"listing_id":"listing-1","buyer_id":"Bob"}'
# Test 8: Alice cannot place an order for Bob (403).
status="$(post http://127.0.0.1:8080/orders "$order" "$alice_token" out/attack/order-attack.json)"
expect "$status" 403 out/attack/order-attack.json

admin_order='{"listing_id":"listing-1","buyer_id":"course-admin"}'
# Test 9: Admin cannot place an order (403).
status="$(post http://127.0.0.1:8080/orders "$admin_order" "$admin_token" out/attack/admin-order.json)"
expect "$status" 403 out/attack/admin-order.json

# Test 10: Alice cannot read Bob's account (403).
status="$(curl -sS -o out/attack/account-attack.json -w '%{http_code}' \
  -H "Authorization: Bearer $alice_token" \
  http://127.0.0.1:8080/accounts/Bob)"
expect "$status" 403 out/attack/account-attack.json

./scripts/stop.sh

echo "Project 3 attack test passed."
echo "Responses are saved in out/attack/."
echo "Services are stopped; the Postgres volume and signing keys are preserved."
