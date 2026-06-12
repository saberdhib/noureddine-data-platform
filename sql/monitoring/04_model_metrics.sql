-- =============================================================================
-- NOUREDDINE — Bloc 4 — Model monitoring metrics
-- Holds the key metrics extracted from each Evidently run, consumed by the
-- Grafana "Model Health" panel. Created idempotently.
-- NOTE: the `monitoring` schema is also used by Bloc 3 (pipeline_runs). We only
-- add to it here; we never drop Bloc 3 objects.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS monitoring;

CREATE TABLE IF NOT EXISTS monitoring.model_metrics (
    metric_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    measured_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version    VARCHAR(50),
    drift_score      NUMERIC(6,4),         -- share of drifted features (0..1)
    n_drifted        INTEGER,
    n_features       INTEGER,
    target_drift     NUMERIC(6,4),
    mape             NUMERIC(8,4),         -- MAPE on the current window
    rmse             NUMERIC(10,4),
    report_path      TEXT,                 -- path to the Evidently HTML report
    breached         BOOLEAN DEFAULT FALSE,-- true if a threshold was crossed
    note             TEXT
);

CREATE INDEX IF NOT EXISTS idx_model_metrics_measured_at
    ON monitoring.model_metrics (measured_at DESC);

-- Lightweight retrain-event log so Grafana can annotate promotions.
CREATE TABLE IF NOT EXISTS monitoring.retrain_events (
    event_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version VARCHAR(50),
    current_mape  NUMERIC(8,4),
    new_mape      NUMERIC(8,4),
    promoted      BOOLEAN,
    reason        TEXT
);
