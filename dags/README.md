# Airflow DAGs

## Bloc 3 — ingestion / transformation (pipelines)
- `ingest_orders.py` — simulator → bronze → dbt (silver/gold) → quality (Elementary).
  *(Bloc 3 scope; the Bloc 4 retrain gate reads its `monitoring.pipeline_runs` status.)*

## Bloc 4 — AI/MLOps

### `retrain_model.py` — weekly retraining (Sundays 02:00) + on-demand trigger
```
check_upstream_quality  ->  extract_training_data  ->  train_and_validate
   ->  update_model_card  ->  write_retrain_metadata
```
- `check_upstream_quality` — P-04 gate: aborts if the last `monitoring.pipeline_runs` failed.
- `train_and_validate` — runs `ml/src/retrain.py`: train → validate on 30d holdout →
  promote IF `new_mape <= current_mape * 1.05` ELSE hold (atomic symlink swap). Logs to
  `monitoring.retrain_events`.
- `update_model_card` — regenerates the model card.

### `monitor_model.py` — daily monitoring (01:00) with drift-triggered retrain
```
generate_evidently_report  ->  check_thresholds  ->  [ trigger_retrain | no_action ]
```
- `generate_evidently_report` — runs `monitoring/evidently/generate_report.py`
  (set `FORCE_DRIFT=1` to demo a breach).
- `check_thresholds` — branch on the latest `monitoring.model_metrics` row vs
  `DRIFT_THRESHOLD` / `MAPE_THRESHOLD`.
- `trigger_retrain` — `TriggerDagRunOperator` → `retrain_model`.

## Notes
- Heavy ML imports happen *inside* tasks so the DAGs parse even on a minimal scheduler.
- In Docker, the Airflow image installs the ML deps via `_PIP_ADDITIONAL_REQUIREMENTS`
  and mounts `../ml` + `../monitoring`. Validate parsing with a DagBag import test.
