#!/usr/bin/env bash
# =============================================================================
# upload-brand.sh — Upload brand / marketing assets into the MinIO 'brand' bucket.
# Digital Asset Management: brand media (logo, campaign visuals, product shots)
# live in the object store alongside the medallion layers.
#
# Usage:  put files under ./brand-assets/ then run:  bash infra/scripts/upload-brand.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
[[ -f "${ENV_FILE}" ]] && { set -a; source "${ENV_FILE}"; set +a; }

USER="${MINIO_ROOT_USER:-minio_admin}"
PASS="${MINIO_ROOT_PASSWORD:-change_me_minio}"
SRC="${ROOT_DIR}/brand-assets"

if [[ ! -d "${SRC}" ]] || [[ -z "$(ls -A "${SRC}" 2>/dev/null)" ]]; then
    echo "Nothing to upload — put files under ${SRC}/ first."
    exit 0
fi

echo "==> Uploading ${SRC} -> s3://brand/"
docker run --rm --network infra_noureddine_net \
    -v "${SRC}:/assets:ro" \
    -e MC_HOST_m="http://${USER}:${PASS}@minio:9000" \
    minio/mc:latest cp --recursive /assets/ m/brand/

echo "==> Contents of s3://brand/:"
docker run --rm --network infra_noureddine_net \
    -e MC_HOST_m="http://${USER}:${PASS}@minio:9000" \
    minio/mc:latest ls --recursive m/brand/
