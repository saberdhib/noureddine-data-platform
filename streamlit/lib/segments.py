"""Customer segmentation (Bloc 4) — RFM + KMeans on pseudonymised customers.

Operates on the gold star schema keyed by ``customer_key`` (a surrogate, NOT a name
or email) plus behavioural aggregates. The clustering is unsupervised; only the
per-segment AGGREGATE profiles are ever exposed to the LLM (no PII — CRM use case,
distinct from the PII-free forecasting model of DPIA #2).
"""
from __future__ import annotations

import pandas as pd

from . import db

# Numeric RFM+ feature set used for clustering.
FEATURES = ["recency_days", "frequency", "monetary", "aov", "discount_rate", "tenure_days"]


def customer_features(today: pd.Timestamp) -> pd.DataFrame:
    """Per-customer RFM + behavioural features (pseudonymised by customer_key)."""
    df = db.run_query("""
        SELECT f.customer_key,
               COUNT(DISTINCT f.order_id)           AS frequency,
               SUM(f.revenue)                       AS monetary,
               SUM(f.quantity)                      AS units,
               SUM(f.discount)                      AS total_discount,
               MAX(d.date)                          AS last_order,
               MIN(d.date)                          AS first_order
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON d.date_key = f.date_key
        GROUP BY f.customer_key
    """)
    if df.empty:
        return df
    last = pd.to_datetime(df["last_order"])
    first = pd.to_datetime(df["first_order"])
    df["recency_days"] = (pd.Timestamp(today) - last).dt.days.clip(lower=0)
    df["tenure_days"] = (last - first).dt.days.clip(lower=0)
    df["aov"] = (df["monetary"] / df["frequency"]).round(2)
    df["discount_rate"] = (df["total_discount"] / df["monetary"].where(df["monetary"] > 0, 1)).clip(0, 1)
    return df


def cluster(df: pd.DataFrame, k: int = 4) -> pd.DataFrame:
    """Standardise the RFM+ features and assign each customer a KMeans segment."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    out = df.copy()
    X = out[FEATURES].fillna(0.0)
    Xs = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    out["segment"] = km.fit_predict(Xs).astype(int)
    return out


def profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-segment profile (no PII) — ready to ground an LLM naming prompt."""
    g = (df.groupby("segment")
         .agg(clients=("customer_key", "count"),
              recence_j=("recency_days", "mean"),
              frequence=("frequency", "mean"),
              valeur_totale_eur=("monetary", "mean"),
              panier_moyen_eur=("aov", "mean"),
              taux_promo=("discount_rate", "mean"),
              anciennete_j=("tenure_days", "mean"))
         .round(1).reset_index())
    total = g["clients"].sum()
    g["part_%"] = (100 * g["clients"] / total).round(1)
    return g.sort_values("valeur_totale_eur", ascending=False).reset_index(drop=True)
