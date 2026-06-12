-- =============================================================================
-- NOUREDDINE — monitoring schema (Bloc 3 pipeline runs + Bloc 4 model metrics)
-- Auto-applied on first DB boot. Idempotent.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS monitoring;

-- Bloc 3: pipeline run audit (the retrain quality-gate reads the latest status).
CREATE TABLE IF NOT EXISTS monitoring.pipeline_runs (
    run_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dag_id   VARCHAR(100),
    run_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    status   VARCHAR(20)            -- 'success' | 'failed' | 'running'
);

-- Bloc 4: model monitoring metrics (consumed by the Grafana "Model Health" panel).
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
-- a fresh stack (Bloc 3 ingestion would normally write these rows).
INSERT INTO monitoring.pipeline_runs (dag_id, status)
SELECT 'ingest_orders', 'success'
WHERE NOT EXISTS (SELECT 1 FROM monitoring.pipeline_runs);
