#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
ts="$(date +%Y%m%d-%H%M%S)"
db_name="${POSTGRES_DB:-ai_coo}"
db_user="${POSTGRES_USER:-ai_coo}"
out="backups/postgres-${ts}.dump"

docker compose exec -T postgres pg_dump -U "${db_user}" -d "${db_name}" -Fc > "${out}"
echo "postgres backup created: ${out}"
