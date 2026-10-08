#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
docker compose down

umask 077
mkdir -p secrets
chmod 700 secrets
staging_dir="$(mktemp -d secrets/.staging.XXXXXX)"
trap 'rm -rf "$staging_dir"' EXIT

openssl genpkey -algorithm ED25519 -out "$staging_dir/private.pem"
openssl pkey -in "$staging_dir/private.pem" -pubout -out "$staging_dir/public.pem"
head -c 24 /dev/urandom | base64 > "$staging_dir/admin-password"
chmod 600 "$staging_dir/private.pem" "$staging_dir/admin-password"

mv "$staging_dir/private.pem" secrets/private.pem
mv "$staging_dir/public.pem" secrets/public.pem
mv "$staging_dir/admin-password" secrets/admin-password

echo "Signing keys and admin password rotated."
echo "Services are stopped. Run ./scripts/start.sh to use the new secrets."
