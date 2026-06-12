"""Prediction tests — shape, contiguous dates, well-ordered intervals.

The DB access functions are monkeypatched so the test runs without Postgres.
"""
from datetime import date

import lightgbm as lgb
import pandas as pd

import predict as predict_mod
from features import build_training_matrix


def _make_bundle(daily_demand, calendar_df):
    X, y, feat_names, frame, cats = build_training_matrix(daily_demand, calendar_df)
    model = lgb.LGBMRegressor(n_estimators=40, random_state=0)
    model.fit(X, y, categorical_feature=["category_code"])
    return {
        "model": model, "feature_names": feat_names, "categories": cats,
        "rmse_per_category": {c: 2.0 for c in cats}, "global_rmse": 2.0,
    }


def test_predict_shape_dates_and_intervals(monkeypatch, daily_demand, calendar_df):
    bundle = _make_bundle(daily_demand, calendar_df)
    hist = daily_demand[daily_demand["category"] == "Qamis"][["date", "units"]]
    monkeypatch.setattr(predict_mod, "_load_history", lambda eng, cat: hist.copy())
    monkeypatch.setattr(predict_mod, "_load_calendar", lambda eng: calendar_df.copy())

    out = predict_mod.predict("Qamis", horizon=14, today=date(2025, 5, 1),
                              bundle=bundle, engine=object())

    assert list(out.columns) == ["date", "prediction", "lower", "upper"]
    assert len(out) == 14
    # Dates are contiguous daily.
    d = pd.to_datetime(out["date"])
    assert (d.diff().dropna() == pd.Timedelta(days=1)).all()
    # Intervals well-ordered and non-negative.
    assert (out["lower"] <= out["prediction"]).all()
    assert (out["prediction"] <= out["upper"]).all()
    assert (out["lower"] >= 0).all()


def test_predict_horizon_capped(monkeypatch, daily_demand, calendar_df):
    bundle = _make_bundle(daily_demand, calendar_df)
    hist = daily_demand[daily_demand["category"] == "Grooming"][["date", "units"]]
    monkeypatch.setattr(predict_mod, "_load_history", lambda eng, cat: hist.copy())
    monkeypatch.setattr(predict_mod, "_load_calendar", lambda eng: calendar_df.copy())
    out = predict_mod.predict("Grooming", horizon=999, today=date(2025, 5, 1),
                              bundle=bundle, engine=object())
    assert len(out) == 30  # HORIZON_MAX
