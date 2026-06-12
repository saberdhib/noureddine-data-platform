"""Training smoke test on tiny synthetic data (no DB, CI-friendly)."""
import lightgbm as lgb
import numpy as np

from features import FEATURE_COLUMNS, build_training_matrix


def test_model_trains_saves_loads_predicts(tmp_path, daily_demand, calendar_df):
    import joblib

    X, y, feat_names, frame, cats = build_training_matrix(daily_demand, calendar_df)
    model = lgb.LGBMRegressor(n_estimators=40, random_state=0)
    model.fit(X, y, categorical_feature=["category_code"])

    bundle = {"model": model, "feature_names": feat_names, "categories": cats}
    path = tmp_path / "m.pkl"
    joblib.dump(bundle, path)

    loaded = joblib.load(path)
    preds = loaded["model"].predict(X.head(5))
    assert preds.shape == (5,)
    assert np.all(np.isfinite(preds))


def test_feature_matrix_shape(daily_demand, calendar_df):
    X, y, feat_names, frame, cats = build_training_matrix(daily_demand, calendar_df)
    assert list(X.columns) == FEATURE_COLUMNS
    assert len(X) == len(y) == len(frame)
    assert set(cats) == {"Qamis", "Grooming"}
