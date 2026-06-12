"""DPIA #2 enforcement — no PII may ever enter the model feature matrix.

This is the governance commitment from Bloc 1 made *enforceable* (not just
declarative): the build fails if any individual-level column reaches the training
matrix. Runs in the `ml-test` CI job on a tiny synthetic fixture (no DB).
"""
import pandas as pd
import pytest

from features import assert_no_pii, build_training_matrix

# Forbidden individual-level / PII columns (DPIA #2).
FORBIDDEN = {
    "customer_id", "customer_key", "customer_email", "email", "customer_name",
    "address", "phone", "ip_address", "first_name", "last_name", "city",
    "order_id", "order_item_id", "tracking_number",
}


def test_no_pii_in_feature_names(daily_demand, calendar_df):
    """The trained feature columns must be disjoint from every forbidden field."""
    X, y, feature_names, frame, categories = build_training_matrix(daily_demand, calendar_df)
    leaked = set(feature_names) & FORBIDDEN
    assert not leaked, f"PII columns leaked into features (DPIA #2 breach): {leaked}"
    # The feature matrix columns themselves must also be clean.
    assert set(X.columns).isdisjoint(FORBIDDEN), \
        f"PII columns in feature matrix: {set(X.columns) & FORBIDDEN}"


def test_features_are_only_calendar_and_aggregate(daily_demand, calendar_df):
    """Belt-and-braces: every feature is a category code, lag/rolling, or calendar field."""
    _, _, feature_names, _, _ = build_training_matrix(daily_demand, calendar_df)
    allowed_prefixes = ("category_code", "lag_", "rolling_", "days_to_", "in_",
                        "is_weekend", "day_of_week", "month", "week_of_year")
    for name in feature_names:
        assert name.startswith(allowed_prefixes), f"Unexpected (possibly non-aggregate) feature: {name}"


def test_guard_raises_on_injected_pii():
    """The assert_no_pii guard must reject a frame containing a PII column."""
    bad = pd.DataFrame({"customer_email": ["a@b.test"], "units": [3]})
    with pytest.raises(ValueError):
        assert_no_pii(bad)
