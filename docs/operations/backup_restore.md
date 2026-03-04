# Backup and Restore (Postgres + MinIO)

## Postgres backup
Create a compressed dump from running compose stack:

```bash
docker compose exec -T postgres pg_dump -U ai_coo -d ai_coo | gzip > backups/postgres-$(date +%F).sql.gz
```

## Postgres restore
```bash
gunzip -c backups/postgres-YYYY-MM-DD.sql.gz | docker compose exec -T postgres psql -U ai_coo -d ai_coo
```

## MinIO backup (reports bucket)
Use `mc` client (or AWS CLI against MinIO endpoint):

```bash
mc alias set localminio http://localhost:9000 minioadmin minioadmin
mc mirror localminio/reports backups/minio-reports
```

## MinIO restore
```bash
mc alias set localminio http://localhost:9000 minioadmin minioadmin
mc mirror backups/minio-reports localminio/reports --overwrite
```

## Suggested schedule
- Postgres dump: every 24h
- MinIO mirror: every 24h
- Verify restore in staging at least weekly
