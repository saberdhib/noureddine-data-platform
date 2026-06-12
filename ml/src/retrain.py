"""Retraining with validation gate + atomic promotion (Bloc 4).

Process (per CLAUDE.md §9):
  extract gold.fact_sales -> feature engineering -> train LightGBM -> validate on
  held-out 30 days -> IF new_mape <= current_mape * 1.05 THEN promote ELSE keep
  current and log "no-promotion".

Promotion is ATOMIC: ``train`` writes ``model_{timestamp}.pkl`` and load-tests it
before swapping the ``current.pkl`` symlink, so a half-written model is never
served. Old versions beyond the last ``KEEP_VERSIONS`` are pruned.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib

from config import (CURRENT_MODEL, KEEP_VERSIONS, METRICS_FILE, MODELS_DIR,  # noqa: E402
                    PROMOTION_TOLERANCE)


def _current_mape() -> float:
    """Global MAPE of the currently promoted model (inf if none)."""
    if not CURRENT_MODEL.exists():
        return float("inf")
    try:
        bundle = joblib.load(CURRENT_MODEL)
        return float(bundle["metrics"]["global"]["mape"])
    except Exception:
        return float("inf")


def _cleanup_old_versions():
    versions = sorted(MODELS_DIR.glob("model_*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
    promoted = CURRENT_MODEL.resolve().name if CURRENT_MODEL.exists() else None
    for old in versions[KEEP_VERSIONS:]:
        if old.name != promoted:
            old.unlink(missing_ok=True)


def retrain() -> dict:
    """Train a candidate, gate on MAPE, promote or hold. Returns a decision dict."""
    # Import here so a missing DB at import-time doesn't break Airflow DAG parsing.
    from pathlib import Path

    from train import _atomic_promote, train

    current_mape = _current_mape()
    # Train + write the candidate file, but do NOT promote yet — we gate first.
    candidate = train(save=True, promote=False)
    new_mape = float(candidate["global"]["mape"])
    candidate_path = Path(candidate["model_path"])

    promote = new_mape <= current_mape * PROMOTION_TOLERANCE
    decision = {
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "candidate_version": candidate["version"],
        "current_mape": None if current_mape == float("inf") else round(current_mape, 4),
        "new_mape": round(new_mape, 4),
        "tolerance": PROMOTION_TOLERANCE,
        "promoted": bool(promote),
        "reason": "promoted" if promote else "no-promotion (candidate worse than tolerance)",
    }

    if promote:
        _atomic_promote(candidate_path)   # atomic swap of current.pkl
        _cleanup_old_versions()
        print(f"PROMOTED {candidate_path.name}: new MAPE {new_mape:.4f} <= {current_mape:.4f} x {PROMOTION_TOLERANCE}")
    else:
        candidate_path.unlink(missing_ok=True)  # discard rejected candidate
        print(f"NO-PROMOTION: new MAPE {new_mape:.4f} > current {current_mape:.4f} x {PROMOTION_TOLERANCE}")

    (MODELS_DIR / "last_retrain.json").write_text(json.dumps(decision, indent=2))
    print(f"Retrain decision: {decision}")
    return decision


if __name__ == "__main__":
    retrain()
