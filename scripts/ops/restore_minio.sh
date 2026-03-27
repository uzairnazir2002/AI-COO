#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <minio_backup_tar_gz>"
  exit 1
fi

archive="$1"
docker compose exec -T minio sh -lc "rm -rf /data/*"
cat "${archive}" | docker compose exec -T minio sh -lc "tar -C / -xzf -"
echo "minio restore completed from: ${archive}"
