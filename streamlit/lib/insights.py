"""PII-safe business snapshots for the LLM features (Bloc 4).

Every function returns plain, category-level aggregates (no PII — DPIA #2) ready to
be JSON-serialised and grounded into an LLM prompt. Sources: the governed `gold`
star schema, `oltp.inventory`/`oltp.products` (aggregated) and the FastAPI forecast.
"""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Dict, List

import pandas as pd

from . import api_client, db


def _round_records(df: pd.DataFrame) -> List[Dict]:
    return json.loads(df.round(2).to_json(orient="records"))


def executive_snapshot(start: str, end: str) -> Dict:
    """KPIs + top categories/channels for the selected period."""
    k = db.kpis(start, end).iloc[0]
    return {
        "periode": {"du": start, "au": end},
        "kpis": {
            "revenue_eur": round(float(k["revenue"]), 0),
            "commandes": int(k["orders"]),
            "unites": int(k["units"]),
            "panier_moyen_eur": round(float(k["aov"]), 1),
        },
        "top_categories": _round_records(db.top_categories(start, end)),
        "top_canaux": _round_records(db.top_channels(start, end)),
    }


def _stock_value() -> pd.DataFrame:
    """Inventory units AND retail value (€) per category — aggregated, no PII."""
    return db.run_query("""
        SELECT p.category AS category,
               SUM(i.stock_quantity)                  AS stock_units,
               SUM(i.stock_quantity * op.price_eur)   AS stock_value_eur
        FROM oltp.inventory i
        JOIN oltp.products op ON op.product_id = i.product_id
        JOIN gold.dim_product p ON p.product_id = i.product_id
        GROUP BY p.category ORDER BY p.category
    """)


def _trend_pct(category: str, window: int = 14) -> float | None:
    """Recent demand trend: % change of last `window` days vs the previous `window`."""
    hist = db.category_history(category, days=window * 2).sort_values("date")
    if len(hist) < window + 2:
        return None
    recent = hist.tail(window)["units"].sum()
    prev = hist.head(len(hist) - window)["units"].sum()
    if prev <= 0:
        return None
    return round(100.0 * (recent - prev) / prev, 1)


def marketing_signals(today: pd.Timestamp, lead_time: int = 21,
                      cover_target: int = 30) -> Dict:
    """Per-category signals to spot sales drops and dormant (over-stocked) value."""
    stock = _stock_value()
    events = db.calendar_events()
    upcoming = events[(pd.to_datetime(events["start_date"]) >= today)
                      & (pd.to_datetime(events["start_date"]) <= today + pd.Timedelta(days=60))]
    rows: List[Dict] = []
    for _, r in stock.iterrows():
        cat = r["category"]
        units = float(r["stock_units"] or 0)
        value = float(r["stock_value_eur"] or 0)
        trend = _trend_pct(cat)
        try:
            fc = api_client.predict(cat, cover_target)
            pred_30d = float(fc["prediction"].sum())
            mean_daily = max(0.01, pred_30d / max(1, len(fc)))
        except Exception:
            pred_30d, mean_daily = None, None
        cover = round(units / mean_daily, 1) if mean_daily else None
        # over-stocked / slow-moving capital: cover well beyond the reorder lead time.
        dormant = bool(cover is not None and cover > max(45, lead_time * 2))
        chute = bool(trend is not None and trend <= -15)
        rows.append({
            "categorie": cat,
            "stock_unites": int(units),
            "stock_valeur_eur": round(value, 0),
            "tendance_14j_pct": trend,
            "demande_prevue_30j": round(pred_30d, 1) if pred_30d is not None else None,
            "jours_de_couverture": cover,
            "stock_dormant": dormant,
            "chute_ventes": chute,
        })
    evs = [{"evenement": e["event_name"], "type": e["event_type"],
            "jours_avant": int((pd.Timestamp(e["start_date"]) - today).days)}
           for _, e in upcoming.iterrows()]
    dormant_value = round(sum(x["stock_valeur_eur"] for x in rows if x["stock_dormant"]), 0)
    return {
        "date_du_jour": today.date().isoformat(),
        "lead_time_days": lead_time,
        "valeur_stock_dormant_eur": dormant_value,
        "categories_en_chute": [x["categorie"] for x in rows if x["chute_ventes"]],
        "categories_stock_dormant": [x["categorie"] for x in rows if x["stock_dormant"]],
        "categories": rows,
        "evenements_a_venir": evs,
    }


def forecast_snapshot(category: str, today: pd.Timestamp, horizon: int = 30) -> Dict:
    """Recent actuals + the J+`horizon` forecast + upcoming events for one category."""
    hist = db.category_history(category, days=30).sort_values("date")
    fc = api_client.predict(category, horizon)
    events = db.calendar_events()
    upcoming = events[(pd.to_datetime(events["start_date"]) >= today)
                      & (pd.to_datetime(events["start_date"]) <= today + pd.Timedelta(days=horizon))]
    return {
        "categorie": category,
        "date_du_jour": today.date().isoformat(),
        "historique_30j": {
            "unites_total": int(hist["units"].sum()) if not hist.empty else 0,
            "moy_jour": round(float(hist["units"].mean()), 2) if not hist.empty else 0,
        },
        "prevision": {
            "horizon_jours": horizon,
            "unites_total_prevues": round(float(fc["prediction"].sum()), 1) if not fc.empty else 0,
            "moy_jour_prevue": round(float(fc["prediction"].mean()), 2) if not fc.empty else 0,
            "pic_prevu": round(float(fc["prediction"].max()), 1) if not fc.empty else 0,
        },
        "evenements_dans_lhorizon": [
            {"evenement": e["event_name"], "type": e["event_type"],
             "jours_avant": int((pd.Timestamp(e["start_date"]) - today).days)}
            for _, e in upcoming.iterrows()
        ],
    }


def data_overview(today: pd.Timestamp) -> Dict:
    """Compact, all-category snapshot used to ground the natural-language data chat."""
    end = today.date().isoformat()
    start = (today - timedelta(days=90)).date().isoformat()
    snap = executive_snapshot(start, end)
    signals = marketing_signals(today)
    return {
        "apercu_90j": snap,
        "stock_et_demande_par_categorie": signals["categories"],
        "evenements_a_venir": signals["evenements_a_venir"],
        "valeur_stock_dormant_eur": signals["valeur_stock_dormant_eur"],
    }
