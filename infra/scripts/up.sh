#!/usr/bin/env bash
# =============================================================================
# up.sh — Bring the NOUREDDINE Data Platform stack up
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

echo "==> NOUREDDINE Data Platform — bringing stack up"

# Copy .env.example if .env is missing
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "  .env not found — copying from .env.example"
    cp "${ROOT_DIR}/.env.example" "${ENV_FILE}"
    echo "  Edit .env with real secrets if needed, then re-run this script."
fi

cd "${ROOT_DIR}"
docker compose -f infra/docker-compose.yml --env-file .env up -d --remove-orphans

echo ""
echo "==> Stack is starting. Run infra/scripts/healthcheck.sh to verify all services."
echo ""
echo "  pgAdmin  : http://localhost:${PGADMIN_PORT:-5050}"
echo "  MinIO    : http://localhost:${MINIO_CONSOLE_PORT:-9001}"
echo "  Airflow  : http://localhost:${AIRFLOW_PORT:-8080}"
echo ""
