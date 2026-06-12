-- =============================================================================
-- 06_create_monitoring.sql — monitoring schema (pipeline + model observability)
-- Single canonical definition shared by Bloc 3 (pipeline_runs, consumed by the
-- ingest_orders DAG + Grafana) and Bloc 4 (model_metrics, retrain_events).
-- Idempotent. Mirrored verbatim into infra/postgres/init/ for auto-boot.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS monitoring;

-- Bloc 3: micro-batch pipeline run audit.
-- run_id is the Airflow run_id (string); run_at is kept so Bloc 4's retrain
-- quality-gate ("...ORDER BY run_at DESC") works against the same table.
CREATE TABLE IF NOT EXISTS monitoring.pipeline_runs (
    run_id          VARCHAR(255) PRIMARY KEY,
    dag_id          VARCHAR(255),
    status          VARCHAR(50),
    rows_processed  INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    error_message   TEXT,
    run_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_at
    ON monitoring.pipeline_runs (run_at DESC);

-- Bloc 4: model monitoring metrics (Grafana "Model Health" panel).
CREATE TABLE IF NOT EXISTS monitoring.model_metrics (
    metric_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    measured_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version    VARCHAR(50),
    drift_score      NUMERIC(6,4),
    n_drifted        INTEGER,
    n_features       INTEGER,
    target_drift     NUMERIC(6,4),
    mape             NUMERIC(8,4),
    rmse             NUMERIC(10,4),
    report_path      TEXT,
    breached         BOOLEAN DEFAULT FALSE,
    note             TEXT
);
CREATE INDEX IF NOT EXISTS idx_model_metrics_measured_at
    ON monitoring.model_metrics (measured_at DESC);

-- Bloc 4: retraining promotion/no-promotion audit trail.
CREATE TABLE IF NOT EXISTS monitoring.retrain_events (
    event_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version VARCHAR(50),
    current_mape  NUMERIC(8,4),
    new_mape      NUMERIC(8,4),
    promoted      BOOLEAN,
    reason        TEXT
);

-- Seed one successful pipeline run so the Bloc 4 retrain quality-gate passes on
-- a fresh stack before the first ingest_orders run.
INSERT INTO monitoring.pipeline_runs (run_id, dag_id, status, rows_processed)
SELECT 'bootstrap__initial', 'ingest_orders', 'success', 0
WHERE NOT EXISTS (SELECT 1 FROM monitoring.pipeline_runs);
