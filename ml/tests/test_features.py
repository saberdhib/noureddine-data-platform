"""Feature-engineering tests, incl. the governance no-PII guard (DPIA #2)."""
import pandas as pd
import pytest

from features import (CALENDAR_FEATURES, FEATURE_COLUMNS, PII_COLUMNS,
                      assert_no_pii, build_feature_frame, build_training_matrix)


def test_no_pii_columns_in_feature_matrix(daily_demand, calendar_df):
    X, y, feat_names, frame, cats = build_training_matrix(daily_demand, calendar_df)
    leaked = PII_COLUMNS.intersection({c.lower() for c in X.columns})
    assert not leaked, f"PII leaked into features: {leaked}"
    assert set(feat_names) == set(FEATURE_COLUMNS)


def test_assert_no_pii_raises_on_pii():
    bad = pd.DataFrame({"customer_id": [1], "units": [2]})
    with pytest.raises(ValueError):
        assert_no_pii(bad)


def test_calendar_features_present_and_flags_correct(daily_demand, calendar_df):
    frame, cats = build_feature_frame(daily_demand, calendar_df)
    for col in CALENDAR_FEATURES:
        assert col in frame.columns
    # A date inside Ramadan must have in_ramadan == 1.
    ramadan_day = frame[frame["date"] == pd.Timestamp("2025-03-15")]
    assert (ramadan_day["in_ramadan"] == 1).all()
    # A normal January day is not in Ramadan.
    jan = frame[frame["date"] == pd.Timestamp("2025-01-10")]
    assert (jan["in_ramadan"] == 0).all()


def test_lag_and_rolling_alignment(daily_demand, calendar_df):
    frame, cats = build_feature_frame(daily_demand, calendar_df)
    one = frame[frame["category"] == "Qamis"].sort_values("date").reset_index(drop=True)
    # lag_7 at position i must equal the target 7 rows earlier.
    assert one.loc[30, "lag_7"] == pytest.approx(one.loc[23, "units"])
    assert one.loc[40, "lag_14"] == pytest.approx(one.loc[26, "units"])
    # rolling_7d at i is the mean of the 7 prior days (shifted, no leakage).
    expected = one.loc[23:29, "units"].mean()
    assert one.loc[30, "rolling_7d"] == pytest.approx(expected)


def test_dense_grid_fills_missing_days(calendar_df):
    # Two categories but one has a gap; grid must be contiguous per category.
    df = pd.DataFrame([
        {"date": pd.Timestamp("2025-01-01"), "category": "Qamis", "units": 5.0},
        {"date": pd.Timestamp("2025-01-03"), "category": "Qamis", "units": 7.0},
        {"date": pd.Timestamp("2025-01-01"), "category": "Grooming", "units": 9.0},
        {"date": pd.Timestamp("2025-01-03"), "category": "Grooming", "units": 4.0},
    ])
    frame, cats = build_feature_frame(df, calendar_df)
    qamis = frame[frame["category"] == "Qamis"]
    assert len(qamis) == 3  # Jan 1,2,3 — the gap day is filled
