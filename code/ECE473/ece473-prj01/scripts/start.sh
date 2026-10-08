#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 0 ]]; then
  echo "Usage: $0" >&2
  echo "Example: $0" >&2
  exit 2
fi

docker rm -f ece573-prj01 >/dev/null 2>&1 || true
docker run --name ece573-prj01 -d -p 8080:8080 ece573-prj01 >/dev/null

for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8080/listings >/dev/null; then
    echo "Marketplace service is ready at http://127.0.0.1:8080."
    exit 0
  fi
  sleep 1
done

echo "Marketplace service did not become ready. Check: docker logs ece573-prj01" >&2
exit 1
