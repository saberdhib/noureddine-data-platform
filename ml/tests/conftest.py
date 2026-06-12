"""Shared fixtures for the ML test-suite (Bloc 4).

Tests use a tiny in-memory synthetic dataset only — they never touch the real
database, so they stay fast and free in CI.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture
def calendar_df():
    """A small calendar covering one of each governed event kind."""
    return pd.DataFrame([
        {"event_name": "Ramadan", "event_type": "religious",
         "start_date": date(2025, 3, 1), "end_date": date(2025, 3, 30)},
        {"event_name": "Aid Al Fitr", "event_type": "religious",
         "start_date": date(2025, 3, 31), "end_date": date(2025, 4, 2)},
        {"event_name": "Aid Al Adha", "event_type": "religious",
         "start_date": date(2025, 6, 7), "end_date": date(2025, 6, 10)},
        {"event_name": "Nikah Season", "event_type": "cultural",
         "start_date": date(2025, 6, 1), "end_date": date(2025, 8, 31)},
        {"event_name": "Black Friday", "event_type": "retail",
         "start_date": date(2025, 11, 28), "end_date": date(2025, 11, 28)},
    ])


@pytest.fixture
def daily_demand():
    """120 days of synthetic demand for two categories."""
    rng = np.random.default_rng(0)
    dates = pd.date_range("2025-01-01", periods=120, freq="D")
    rows = []
    for cat, base in [("Qamis", 20), ("Grooming", 30)]:
        for d in dates:
            units = max(0, base + (5 if d.weekday() >= 5 else 0) + int(rng.normal(0, 3)))
            rows.append({"date": d, "category": cat, "units": float(units)})
    return pd.DataFrame(rows)
