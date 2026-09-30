#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  exit 2
fi

cd "$(dirname "$0")/.."
docker compose up -d --build

for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8080/listings >/dev/null; then
    echo "Marketplace service is ready at http://127.0.0.1:8080."
    exit 0
  fi
  sleep 1
done

echo "Marketplace service did not become ready." >&2
echo "Check: docker compose ps" >&2
echo "Check: docker compose logs marketplace-service postgres" >&2
exit 1

