#!/usr/bin/env bash
# =============================================================================
# healthcheck-bloc2.sh — Verify the BLOC 2 scope only (Data Architecture)
# Scope: postgres, minio, pgadmin, airflow + schemas/data + buckets + DAG visible.
# Bloc 3/4 services (api, streamlit, grafana) are intentionally NOT checked here.
# Exits 0 if everything in the Bloc 2 perimeter is green.
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
AIRFLOW_PORT="${AIRFLOW_PORT:-8080}"

FAIL=0

ok()   { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo ""
echo "============================================="
echo " NOUREDDINE — Health Check (BLOC 2 perimeter)"
echo "============================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Container health status (Bloc 2 services only)
# ---------------------------------------------------------------------------
echo "── Container health ────────────────────"
for svc in postgres minio pgadmin airflow; do
    container="noureddine_${svc}"
    status=$(docker inspect --format='{{.State.Health.Status}}' "${container}" 2>/dev/null || echo "not_found")
    if [[ "${status}" == "healthy" ]]; then
        ok "${container}: ${status}"
    else
        fail "${container}: ${status}"
    fi
done

mc_exit=$(docker inspect --format='{{.State.ExitCode}}' noureddine_minio_init 2>/dev/null || echo "?")
if [[ "${mc_exit}" == "0" ]]; then
    ok "noureddine_minio_init: exited 0 (success)"
else
    fail "noureddine_minio_init: exit code ${mc_exit}"
fi

echo ""

# ---------------------------------------------------------------------------
# 2. PostgreSQL — medallion schemas + tables present, seed rows loaded
# ---------------------------------------------------------------------------
echo "── PostgreSQL schema & data (medallion) ─"

psql_exec() {
    docker exec noureddine_postgres \
        psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "$1" 2>/dev/null
}

# Medallion schemas exist
schema_count=$(psql_exec "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name IN ('oltp','bronze','silver','gold');" | tr -d '[:space:]')
if [[ "${schema_count}" == "4" ]]; then
    ok "schemas oltp/bronze/silver/gold: all present"
else
    fail "medallion schemas: expected 4, got ${schema_count}"
fi

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

view_count=$(psql_exec "SELECT COUNT(*) FROM pg_views WHERE schemaname='gold';" | tr -d '[:space:]')
if [[ "${view_count}" -ge 3 ]]; then
    ok "gold views: ${view_count} views present"
else
    fail "gold views: expected >= 3, got ${view_count}"
fi

echo ""

# ---------------------------------------------------------------------------
# 3. MinIO — S3-compatible buckets present
# ---------------------------------------------------------------------------
echo "── MinIO buckets (data lake) ───────────"
for bucket in bronze silver gold; do
    status_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "${MINIO_ROOT_USER}:${MINIO_ROOT_PASSWORD}" \
        "http://localhost:${MINIO_API_PORT}/${bucket}/" 2>/dev/null || echo "000")
    if [[ "${status_code}" == "200" || "${status_code}" == "403" || "${status_code}" == "301" ]]; then
        ok "bucket '${bucket}': accessible (HTTP ${status_code})"
    else
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
# 4. Airflow — orchestrator reachable + DAG visible
# ---------------------------------------------------------------------------
echo "── Airflow (orchestrator) ──────────────"
af_code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${AIRFLOW_PORT}/health" 2>/dev/null || echo "000")
[[ "${af_code}" == "200" ]] && ok "Airflow webserver /health (HTTP ${af_code})" || fail "Airflow webserver (HTTP ${af_code})"

dag_present=$(docker exec noureddine_airflow airflow dags list 2>/dev/null | grep -c "ingest_orders" || true)
if [[ "${dag_present}" -ge 1 ]]; then
    ok "DAG 'ingest_orders': visible to scheduler"
else
    fail "DAG 'ingest_orders': not visible"
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================="
if [[ "${FAIL}" -eq 0 ]]; then
    echo " ✅  BLOC 2 — all checks passed!"
else
    echo " ❌  BLOC 2 — ${FAIL} check(s) failed."
fi
echo "============================================="
echo ""

[[ "${FAIL}" -eq 0 ]]
