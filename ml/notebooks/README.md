# `ml/notebooks/` — EDA & Feature Analysis (consigne `/notebooks`)

Exploratory analysis supporting the modelling choices in Bloc 4.

Recommended notebooks (run against the local stack):
- `01_eda_demand.ipynb` — daily demand per category, weekly seasonality, calendar
  peaks (Ramadan, pre-Eid windows, Nikah season, Black Friday).
- `02_feature_analysis.ipynb` — lag/rolling correlation, calendar-feature signal.
- `03_shap_review.ipynb` — load `ml/models/current.pkl`, review `shap_summary.png`,
  confirm calendar proximity + recent demand dominate (and **no PII** features exist).

> Notebooks are exploratory and not part of CI. The production code paths live in
> `ml/src/`. Keep any saved outputs free of personal data (synthetic only).
