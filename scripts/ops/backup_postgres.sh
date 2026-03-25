#!/usr/bin/env bash
# Логический backup PostgreSQL (pg_dump custom format). SME §1.1.
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL (postgresql://...)}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/dental_booking_${STAMP}.dump"

pg_dump "$DATABASE_URL" -Fc -f "$OUT"
SIZE="$(stat -c%s "$OUT" 2>/dev/null || stat -f%z "$OUT")"
if [ "${SIZE:-0}" -lt 1 ]; then
  echo "backup failed: empty file $OUT" >&2
  exit 1
fi
echo "OK: $OUT ($SIZE bytes)"
