#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
for file in secrets/private.pem secrets/public.pem secrets/admin-password; do
  if [[ ! -s "$file" ]]; then
    echo "Missing or empty local secret: $file" >&2
    echo "Run ./scripts/rotate-secrets.sh to create or replace the keys and admin password." >&2
    exit 1
  fi
done

docker compose up -d --build

for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:8080/healthz >/dev/null &&
     curl -fsS http://127.0.0.1:8081/healthz >/dev/null; then
    echo "Marketplace service is ready at http://127.0.0.1:8080."
    echo "Login service is ready at http://127.0.0.1:8081."
    exit 0
  fi
  sleep 1
done

echo "Services did not become ready." >&2
echo "Check: docker compose ps" >&2
echo "Check: docker compose logs marketplace-service login-service postgres" >&2
exit 1
