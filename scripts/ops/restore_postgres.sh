#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <postgres_dump_file>"
  exit 1
fi

dump_file="$1"
db_name="${POSTGRES_DB:-ai_coo}"
db_user="${POSTGRES_USER:-ai_coo}"

cat "${dump_file}" | docker compose exec -T postgres pg_restore -U "${db_user}" -d "${db_name}" --clean --if-exists
echo "postgres restore completed from: ${dump_file}"
