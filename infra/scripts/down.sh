#!/usr/bin/env bash
# =============================================================================
# down.sh — Tear the NOUREDDINE Data Platform stack down
# Usage: ./down.sh           — stops containers, keeps volumes
#        ./down.sh --volumes — stops containers AND removes volumes (full reset)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${ROOT_DIR}"

if [[ "${1:-}" == "--volumes" ]]; then
    echo "==> Tearing down stack and removing all data volumes (full reset)"
    docker compose -f infra/docker-compose.yml --env-file .env down -v
else
    echo "==> Stopping stack (data volumes preserved)"
    docker compose -f infra/docker-compose.yml --env-file .env down
fi

echo "==> Done."
