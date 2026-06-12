# `ml/retrain/` — Retraining (consigne `/retrain`)

The retraining **logic** lives in `ml/src/retrain.py`; the **orchestration** lives in
`dags/retrain_model.py` (scheduled) and `dags/monitor_model.py` (drift-triggered).
This folder documents the contract (the consigne expects a top-level `/retrain`).

## Dual trigger
- **Scheduled:** `retrain_model` DAG, Sundays 02:00.
- **Drift-triggered:** `monitor_model` DAG (daily) → on threshold breach →
  `TriggerDagRunOperator` → `retrain_model`.

## Process (`ml/src/retrain.py`)
1. Read current model's global MAPE.
2. Train a candidate (`train.py`, save the timestamped file, **do not promote yet**).
3. **Gate:** promote iff `new_mape <= current_mape * 1.05`, else discard the candidate
   and log `no-promotion`.
4. **Atomic promotion:** load-test the candidate, then swap the `current.pkl` symlink
   (`tmp` symlink + `os.replace`) — a half-written model is never served.
5. Keep the last 5 versions for rollback; prune the rest.
6. Decision is written to `ml/models/last_retrain.json` and `monitoring.retrain_events`.

## Run manually
```bash
python ml/src/retrain.py
# or, via the API (admin):
curl -X POST localhost:8000/retrain -H "X-API-Key: $API_KEY"
```
