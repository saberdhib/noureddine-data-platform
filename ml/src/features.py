"""Feature engineering for the demand-forecasting model (Bloc 4).

Target: **daily units sold per category** (``category x day``).

Hard governance rule (DPIA #2): **no PII may enter the feature matrix**. Only
aggregate, category-level demand and calendar-derived columns are allowed. The
``assert_no_pii`` helper is called everywhere a feature frame is produced and is
also enforced by a unit test (``tests/test_features.py``).

Calendar features are derived from ``oltp.calendar_events`` (the SAME fixed
windows produced upstream) — Hijri dates are NEVER recomputed here.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

# Columns that must NEVER appear in the training matrix (individual-level / PII).
PII_COLUMNS = {
    "customer_id", "customer_key", "customer_email", "email", "customer_name",
    "first_name", "last_name", "address", "city", "phone", "order_id",
    "order_item_id", "tracking_number",
}

TARGET = "units"

CALENDAR_FEATURES = [
    "days_to_next_eid_fitr", "days_to_next_eid_adha", "days_to_ramadan_start",
    "days_to_black_friday", "in_ramadan", "in_pre_eid_window",
    "in_nikah_season", "is_weekend", "day_of_week", "month", "week_of_year",
]
LAG_FEATURES = ["lag_7", "lag_14", "lag_30"]
ROLLING_FEATURES = ["rolling_7d", "rolling_30d"]
FEATURE_COLUMNS = ["category_code"] + LAG_FEATURES + ROLLING_FEATURES + CALENDAR_FEATURES


def assert_no_pii(df: pd.DataFrame) -> None:
    """Raise if any banned individual-level column leaked into ``df``."""
    leaked = PII_COLUMNS.intersection({c.lower() for c in df.columns})
    if leaked:
        raise ValueError(
            f"PII / individual-level columns are forbidden in features (DPIA #2): {sorted(leaked)}"
        )


# --- calendar helpers --------------------------------------------------------
def _classify_events(df_calendar: pd.DataFrame) -> dict:
    """Bucket calendar rows by kind using tolerant keyword matching.

    Returns a dict of kind -> list of (start_date, end_date) Timestamps.
    """
    buckets = {"ramadan": [], "eid_fitr": [], "eid_adha": [], "nikah": [], "black_friday": []}
    for _, row in df_calendar.iterrows():
        name = str(row.get("event_name", "")).lower()
        etype = str(row.get("event_type", "")).lower()
        blob = f"{name} {etype}"
        start = pd.Timestamp(row["start_date"])
        end = pd.Timestamp(row["end_date"])
        if "ramadan" in blob:
            buckets["ramadan"].append((start, end))
        elif "fitr" in blob:
            buckets["eid_fitr"].append((start, end))
        elif "adha" in blob:
            buckets["eid_adha"].append((start, end))
        elif "nikah" in blob:
            buckets["nikah"].append((start, end))
        elif "black" in blob:
            buckets["black_friday"].append((start, end))
    return buckets


def _within(date: pd.Timestamp, windows) -> int:
    return int(any(s <= date <= e for s, e in windows))


def _days_to_next(date: pd.Timestamp, windows, cap: int = 365) -> int:
    """Days until the next window start at/after ``date`` (capped)."""
    future = [(s - date).days for s, _ in windows if s >= date]
    return min(future) if future else cap


def build_calendar_features(dates: pd.DatetimeIndex, df_calendar: pd.DataFrame) -> pd.DataFrame:
    """Compute the governed calendar features for each date."""
    b = _classify_events(df_calendar)
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        in_pre_eid = int(
            any(0 <= (s - d).days <= 14 for s, _ in b["eid_fitr"] + b["eid_adha"])
        )
        rows.append({
            "date": d,
            "days_to_next_eid_fitr": _days_to_next(d, b["eid_fitr"]),
            "days_to_next_eid_adha": _days_to_next(d, b["eid_adha"]),
            "days_to_ramadan_start": _days_to_next(d, b["ramadan"]),
            "days_to_black_friday": _days_to_next(d, b["black_friday"]),
            "in_ramadan": _within(d, b["ramadan"]),
            "in_pre_eid_window": in_pre_eid,
            "in_nikah_season": _within(d, b["nikah"]),
            "is_weekend": int(d.weekday() >= 5),
            "day_of_week": d.weekday(),
            "month": d.month,
            "week_of_year": int(d.isocalendar().week),
        })
    return pd.DataFrame(rows)


# --- main entry point --------------------------------------------------------
def build_feature_frame(daily: pd.DataFrame, df_calendar: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Build the full feature frame from a daily ``category x date`` demand table.

    ``daily`` must have columns ``date``, ``category``, ``units``. Missing
    category-days are filled with zero so lags/rolling windows are contiguous.
    Returns ``(frame, categories)`` where ``frame`` includes ``date``,
    ``category``, the feature columns and the target ``units``.
    """
    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    categories = sorted(daily["category"].dropna().unique().tolist())

    # Dense category x date grid (fill gaps with 0 demand).
    full_dates = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    grid = pd.MultiIndex.from_product([categories, full_dates], names=["category", "date"])
    daily = (
        daily.groupby(["category", "date"], as_index=False)[TARGET].sum()
        .set_index(["category", "date"]).reindex(grid, fill_value=0.0).reset_index()
    )

    # Calendar features (computed once per date, broadcast to every category).
    cal = build_calendar_features(full_dates, df_calendar)
    daily = daily.merge(cal, on="date", how="left")

    # Per-category autoregressive features (shifted to avoid target leakage).
    daily = daily.sort_values(["category", "date"]).reset_index(drop=True)
    g = daily.groupby("category")[TARGET]
    daily["lag_7"] = g.shift(7)
    daily["lag_14"] = g.shift(14)
    daily["lag_30"] = g.shift(30)
    daily["rolling_7d"] = g.shift(1).rolling(7).mean().reset_index(level=0, drop=True)
    daily["rolling_30d"] = g.shift(1).rolling(30).mean().reset_index(level=0, drop=True)

    # Categorical encoding for LightGBM.
    cat_dtype = pd.CategoricalDtype(categories=categories, ordered=False)
    daily["category_code"] = daily["category"].astype(cat_dtype).cat.codes

    daily = daily.fillna(0.0)
    assert_no_pii(daily)
    return daily, categories


def build_training_matrix(daily: pd.DataFrame, df_calendar: pd.DataFrame):
    """Convenience wrapper returning ``X, y, feature_names, frame, categories``."""
    frame, categories = build_feature_frame(daily, df_calendar)
    X = frame[FEATURE_COLUMNS].copy()
    y = frame[TARGET].copy()
    assert_no_pii(X)
    return X, y, FEATURE_COLUMNS, frame, categories
