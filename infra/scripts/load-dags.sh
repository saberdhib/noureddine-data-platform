#!/usr/bin/env bash
# =============================================================================
# load-dags.sh — Copy DAG files into the airflow_dags named volume.
# Needed because on macOS/VirtioFS, bind-mounting the dags folder makes Airflow's
# locked reads deadlock (OSError 35). The DAGs live in a named volume instead;
# this script (re)loads them from the repo via `docker cp` (reads the host fs
# directly, bypassing the FUSE bind mount). Run once after `up.sh`, and again
# whenever you change a DAG. The volume persists across container recreation.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONTAINER="noureddine_airflow"

echo "==> Loading DAGs into ${CONTAINER}:/opt/airflow/dags"
docker exec "${CONTAINER}" mkdir -p /opt/airflow/dags

for f in "${ROOT_DIR}"/dags/*.py; do
    [ -e "$f" ] || continue
    docker cp "$f" "${CONTAINER}:/opt/airflow/dags/$(basename "$f")"
    echo "  copied $(basename "$f")"
done

echo "==> Reserializing DAGs"
docker exec "${CONTAINER}" airflow dags reserialize >/dev/null 2>&1 || true

echo "==> DAGs now visible:"
docker exec "${CONTAINER}" airflow dags list 2>/dev/null
