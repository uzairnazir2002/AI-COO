#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <postgres_dump_file> <minio_backup_tar_gz>"
  exit 1
fi

pg_dump_file="$1"
minio_backup_file="$2"
db_user="${POSTGRES_USER:-ai_coo}"
tmp_db="ai_coo_restore_drill"

docker compose exec -T postgres psql -U "${db_user}" -d postgres -c "DROP DATABASE IF EXISTS ${tmp_db};"
docker compose exec -T postgres psql -U "${db_user}" -d postgres -c "CREATE DATABASE ${tmp_db};"
cat "${pg_dump_file}" | docker compose exec -T postgres pg_restore -U "${db_user}" -d "${tmp_db}" --clean --if-exists

row_count=$(docker compose exec -T postgres psql -U "${db_user}" -d "${tmp_db}" -tAc "SELECT COUNT(*) FROM transactions;")
if [[ "${row_count}" -lt 0 ]]; then
  echo "restore drill failed: invalid row count"
  exit 1
fi

docker compose exec -T postgres psql -U "${db_user}" -d postgres -c "DROP DATABASE IF EXISTS ${tmp_db};"

tmp_dir=$(mktemp -d)
tar -xzf "${minio_backup_file}" -C "${tmp_dir}"
if [[ ! -d "${tmp_dir}/data" ]]; then
  echo "restore drill failed: minio archive does not contain /data"
  exit 1
fi
rm -rf "${tmp_dir}"

echo "restore drill passed: postgres dump + minio archive validated"
