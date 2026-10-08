#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")"
mkdir -p out
export AUTH_ENABLED=true

current_step="setup"
expected="services start successfully"
response_file=""
response_body=""

step() {
  current_step="$1"
  expected="$2"
  response_file="${3:-}"
  response_body=""
  printf 'Checking %s...\n' "$current_step"
}

on_error() {
  local status=$?
  local api_error=""
  trap - ERR

  printf 'Acceptance failed during %s (exit %s).\n' "$current_step" "$status" >&2
  printf 'Expected: %s\n' "$expected" >&2
  if [[ -n "$response_file" && -f "$response_file" ]]; then
    printf 'Response: %s\n' "$response_file" >&2
    api_error="$(jq -r '.error // empty' "$response_file" 2>/dev/null || true)"
  elif [[ -n "$response_body" ]]; then
    api_error="$(jq -r '.error // empty' <<< "$response_body" 2>/dev/null || true)"
  fi
  if [[ -n "$api_error" ]]; then
    printf 'API error: %s\n' "$api_error" >&2
  elif [[ -n "$response_file" && -s "$response_file" ]]; then
    printf 'Response body: %s\n' "$(head -c 240 "$response_file" | tr '\n' ' ')" >&2
    if head -n 1 "$response_file" | grep -q '^404 page not found'; then
      echo "Check the protected route registrations in marketplace-service/main.go." >&2
    fi
  fi
  echo "Check: docker compose logs login-service marketplace-service postgres" >&2
  echo "Services remain running for inspection; use ./scripts/stop.sh when done." >&2
  exit "$status"
}
trap on_error ERR

step "database and secret reset" "reset completes"
./scripts/reset.sh

step "service startup" "both services become ready"
./scripts/start.sh

step "admin login" "an access token"
response_body="$(./scripts/admin-login.sh)"
admin_token="$(jq -er .access_token <<< "$response_body" 2>/dev/null)"

step "Alice registration" "balance 0" out/alice-registration.json
printf 'alice-pass\n' | ./scripts/create-account.sh Alice > "$response_file"
jq -e '.balance == 0' "$response_file" &>/dev/null

step "Alice login" "an access token"
response_body="$(printf 'alice-pass\n' | ./scripts/login.sh Alice)"
alice_token="$(jq -er .access_token <<< "$response_body" 2>/dev/null)"

step "Bob registration" "balance 0" out/bob-registration.json
printf 'bob-pass-123\n' | ./scripts/create-account.sh Bob > "$response_file"
jq -e '.balance == 0' "$response_file" &>/dev/null

step "Bob login" "an access token"
response_body="$(printf 'bob-pass-123\n' | ./scripts/login.sh Bob)"
bob_token="$(jq -er .access_token <<< "$response_body" 2>/dev/null)"

step "admin credit grant" "Bob's balance 100" out/bob-grant.json
TOKEN="$admin_token" ./scripts/grant-credits.sh Bob 100 > "$response_file"
jq -e '.balance == 100' "$response_file" &>/dev/null

step "Alice listing" "a listing ID" out/listing.json
TOKEN="$alice_token" ./scripts/list.sh Alice "Used textbook" 25 > "$response_file"
listing_id="$(jq -er .listing_id "$response_file" 2>/dev/null)"

step "public browse" "Alice's listing appears" out/alice-listings.json
./scripts/browse.sh Alice > "$response_file"
jq -e --arg listing_id "$listing_id" '[.listings[].listing_id] | index($listing_id) != null' "$response_file" &>/dev/null

step "Bob order" "completed status" out/order.json
TOKEN="$bob_token" ./scripts/order.sh "$listing_id" Bob > "$response_file"
jq -e '.status == "completed"' "$response_file" &>/dev/null

step "service shutdown" "services stop cleanly"
./scripts/stop.sh

echo "Project 3 acceptance test passed."
echo "Responses are saved in out/."
echo "Services are stopped; the Postgres volume and signing keys are preserved."
