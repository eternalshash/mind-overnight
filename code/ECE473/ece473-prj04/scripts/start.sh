#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
node_count="${CASSANDRA_NODES:-3}"
case "$node_count" in 2|3) ;; *) echo "CASSANDRA_NODES must be 2 or 3" >&2; exit 2 ;; esac
for file in secrets/private.pem secrets/public.pem secrets/admin-password; do
  if [[ ! -s "$file" ]]; then
    echo "Missing or empty local secret: $file" >&2
    echo "Run ./scripts/rotate-secrets.sh to create or replace the keys and admin password." >&2
    exit 1
  fi
done

services=(postgres login-service marketplace-service cassandra-1 cassandra-2)
if [[ "$node_count" == 3 ]]; then
  services+=(cassandra-3)
fi
echo "Starting Postgres, the application services, and $node_count Cassandra nodes. This may take a few minutes."
docker compose up -d --build "${services[@]}"

echo "Waiting for the marketplace and login services to become ready..."
for _ in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:8080/healthz >/dev/null 2>&1 &&
     curl -fsS http://127.0.0.1:8081/healthz >/dev/null 2>&1; then
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
