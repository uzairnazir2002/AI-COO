#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
ts="$(date +%Y%m%d-%H%M%S)"
out="backups/minio-${ts}.tar.gz"

docker compose exec -T minio sh -lc "tar -C / -czf - data" > "${out}"
echo "minio backup created: ${out}"
