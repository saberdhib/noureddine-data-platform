-- monitoring schema — pipeline observability for Grafana (Bloc 3)
CREATE SCHEMA IF NOT EXISTS monitoring;

CREATE TABLE IF NOT EXISTS monitoring.pipeline_runs (
    run_id          VARCHAR(255) PRIMARY KEY,
    dag_id          VARCHAR(255),
    status          VARCHAR(50),
    rows_processed  INTEGER DEFAULT 0,
    started_at      TIMESTAMP,
    ended_at        TIMESTAMP,
    error_message   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);
