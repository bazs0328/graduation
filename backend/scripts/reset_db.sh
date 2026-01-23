#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MYSQL_USER="${MYSQL_USER:-app_user}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-app_pass}"
MYSQL_DATABASE="${MYSQL_DATABASE:-app_db}"

echo "Truncating tables in ${MYSQL_DATABASE}..."
docker compose exec -T db mysql -u"${MYSQL_USER}" -p"${MYSQL_PASSWORD}" -D "${MYSQL_DATABASE}" -e "TRUNCATE TABLE chunks; TRUNCATE TABLE documents;"

echo "Removing local FAISS index files..."
rm -f "${BASE_DIR}/backend/data/faiss.index" "${BASE_DIR}/backend/data/mapping.json"

echo "Done."