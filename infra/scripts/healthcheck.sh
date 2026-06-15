#!/usr/bin/env bash
# =============================================================================
# healthcheck.sh — Verify all NOUREDDINE stack services are healthy
# Exits 0 if everything is green, non-zero on first failure.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

# Load env vars if available
if [[ -f "${ENV_FILE}" ]]; then
    set -a; source "${ENV_FILE}"; set +a
fi

POSTGRES_USER="${POSTGRES_USER:-noureddine_user}"
POSTGRES_DB="${POSTGRES_DB:-noureddine}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minio_admin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-change_me_minio}"
MINIO_API_PORT="${MINIO_API_PORT:-9000}"

PASS=0
FAIL=0

ok()   { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
warn() { echo "  ⚠️  $1"; }  # non-blocking — only required after full Bloc 3 run

echo ""
echo "========================================"
echo " NOUREDDINE Data Platform — Health Check"
echo "========================================"
echo ""

# ---------------------------------------------------------------------------
# 1. Container health status
# ---------------------------------------------------------------------------
echo "── Container health ────────────────────"
for svc in postgres minio pgadmin airflow api streamlit grafana; do
    container="noureddine_${svc}"
    status=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "not_found")
    if [[ "${status}" == "healthy" ]]; then
        ok "${container}: ${status}"
    else
        fail "${container}: ${status}"
    fi
done

# minio-init is a one-shot — just check it exited 0
mc_exit=$(docker inspect --format='{{.State.ExitCode}}' noureddine_minio_init 2>/dev/null || echo "?")
if [[ "${mc_exit}" == "0" ]]; then
    ok "noureddine_minio_init: exited 0 (success)"
else
    fail "noureddine_minio_init: exit code ${mc_exit}"
fi

echo ""

# ---------------------------------------------------------------------------
# 2. PostgreSQL — schemas and tables present, seed rows loaded
# ---------------------------------------------------------------------------
echo "── PostgreSQL schema & data ────────────"

psql_exec() {
    docker exec noureddine_postgres \
        psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "$1" 2>/dev/null
}

check_count() {
    local label="$1"; local query="$2"; local min="${3:-1}"
    local cnt
    cnt=$(psql_exec "${query}" | tr -d '[:space:]')
    if [[ "${cnt}" =~ ^[0-9]+$ ]] && [[ "${cnt}" -ge "${min}" ]]; then
        ok "${label}: ${cnt} rows"
    else
        fail "${label}: got '${cnt}' (expected >= ${min})"
    fi
}

check_count "oltp.customers"       "SELECT COUNT(*) FROM oltp.customers;"       50
check_count "oltp.orders"          "SELECT COUNT(*) FROM oltp.orders;"          50
check_count "oltp.products"        "SELECT COUNT(*) FROM oltp.products;"        50
check_count "oltp.order_items"     "SELECT COUNT(*) FROM oltp.order_items;"     50
check_count "oltp.inventory"       "SELECT COUNT(*) FROM oltp.inventory;"       50
check_count "oltp.calendar_events" "SELECT COUNT(*) FROM oltp.calendar_events;" 8
check_count "gold.fact_sales"      "SELECT COUNT(*) FROM gold.fact_sales;"      1
check_count "gold.dim_customer"    "SELECT COUNT(*) FROM gold.dim_customer;"    50
check_count "gold.dim_product"     "SELECT COUNT(*) FROM gold.dim_product;"     50

# Views exist
view_count=$(psql_exec "SELECT COUNT(*) FROM pg_views WHERE schemaname='gold';" | tr -d '[:space:]')
if [[ "${view_count}" -ge 3 ]]; then
    ok "gold views: ${view_count} views present"
else
    fail "gold views: expected >= 3, got ${view_count}"
fi

echo ""

# ---------------------------------------------------------------------------
# 3. MinIO — buckets present
# ---------------------------------------------------------------------------
echo "── MinIO buckets ───────────────────────"

mc_cmd() {
    docker exec noureddine_minio_init \
        mc "$@" 2>/dev/null || \
    docker run --rm --network noureddine_net \
        -e MC_HOST_local="http://${MINIO_ROOT_USER}:${MINIO_ROOT_PASSWORD}@minio:${MINIO_API_PORT}" \
        minio/mc:latest "$@" 2>/dev/null
}

for bucket in bronze silver gold; do
    # Hit MinIO HTTP API directly
    status_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "${MINIO_ROOT_USER}:${MINIO_ROOT_PASSWORD}" \
        "http://localhost:${MINIO_API_PORT}/${bucket}/" 2>/dev/null || echo "000")
    # 200 = bucket exists, 403 = exists but no list permission (still exists)
    if [[ "${status_code}" == "200" || "${status_code}" == "403" || "${status_code}" == "301" ]]; then
        ok "bucket '${bucket}': accessible (HTTP ${status_code})"
    else
        # Try via docker exec on minio container
        bucket_exists=$(docker exec noureddine_minio \
            /bin/sh -c "[ -d /data/${bucket} ] && echo yes || echo no" 2>/dev/null || echo "no")
        if [[ "${bucket_exists}" == "yes" ]]; then
            ok "bucket '${bucket}': exists (verified via volume)"
        else
            fail "bucket '${bucket}': not found (HTTP ${status_code})"
        fi
    fi
done

echo ""

# ---------------------------------------------------------------------------
# 4. Bloc 4 — model serving, business app, monitoring
# ---------------------------------------------------------------------------
echo "── Bloc 4: AI/MLOps ────────────────────"

API_PORT="${API_PORT:-8000}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"

# FastAPI /health
api_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/health" 2>/dev/null || echo "000")
[[ "${api_code}" == "200" ]] && ok "FastAPI /health (HTTP ${api_code})" || fail "FastAPI /health (HTTP ${api_code})"

# FastAPI auth enforced on /predict (expect 401 without key)
predict_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:${API_PORT}/predict" \
    -H "Content-Type: application/json" -d '{"category":"Qamis","horizon":7}' 2>/dev/null || echo "000")
[[ "${predict_code}" == "401" ]] && ok "FastAPI /predict requires API key (HTTP 401)" || fail "FastAPI /predict auth (got ${predict_code}, expected 401)"

# Streamlit health
st_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${STREAMLIT_PORT}/_stcore/health" 2>/dev/null || echo "000")
[[ "${st_code}" == "200" ]] && ok "Streamlit /_stcore/health (HTTP ${st_code})" || fail "Streamlit health (HTTP ${st_code})"

# Grafana health
gf_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${GRAFANA_PORT}/api/health" 2>/dev/null || echo "000")
[[ "${gf_code}" == "200" ]] && ok "Grafana /api/health (HTTP ${gf_code})" || fail "Grafana health (HTTP ${gf_code})"

# Monitoring tables present
check_count "monitoring.model_metrics (schema present)" \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='monitoring' AND table_name='model_metrics';" 1

# Promoted model present (checked inside the api container's mounted models dir)
model_present=$(docker exec noureddine_api /bin/sh -c "[ -e /app/ml/models/current.pkl ] && echo yes || echo no" 2>/dev/null || echo "no")
[[ "${model_present}" == "yes" ]] && ok "Promoted model current.pkl present" || fail "current.pkl missing (run training / retrain_model)"

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "========================================"
if [[ "${FAIL}" -eq 0 ]]; then
    echo " ✅  All checks passed!"
else
    echo " ❌  ${FAIL} check(s) failed. See above for details."
fi
echo "========================================"
echo ""

[[ "${FAIL}" -eq 0 ]]
