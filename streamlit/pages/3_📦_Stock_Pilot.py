"""Page 3 — Stock Pilot (Bloc 4).

Per category: current inventory vs predicted 30-day demand, days of cover, and a
restock signal. Rows where a calendar event falls within the cover window get an
extra warning. Forecasts come from the FastAPI service.
"""
import os

import pandas as pd
import streamlit as st

from lib import api_client, db

st.set_page_config(page_title="Stock Pilot", page_icon="📦", layout="wide")
st.title("📦 Stock Pilot")
st.caption("Inventory vs predicted demand — restock decision support.")

# Env-tunable thresholds (days of cover).
RED = int(os.getenv("STOCK_RED_DAYS", "7"))
ORANGE = int(os.getenv("STOCK_ORANGE_DAYS", "14"))

inv = db.inventory_by_category()
if inv.empty:
    st.error("No inventory found in oltp.inventory.")
    st.stop()

events = db.calendar_events()
today = pd.Timestamp("2026-06-12")

rows = []
for _, r in inv.iterrows():
    category, stock = r["category"], float(r["stock"])
    try:
        fc = api_client.predict(category, 30)
    except Exception as exc:
        st.error(f"Forecast API not reachable: {exc}")
        st.stop()
    pred_30d = float(fc["prediction"].sum())
    mean_daily = max(0.01, pred_30d / max(1, len(fc)))
    days_cover = stock / mean_daily

    if days_cover < RED:
        signal = "🔴 Reorder now"
    elif days_cover < ORANGE:
        signal = "🟠 Watch"
    else:
        signal = "🟢 OK"

    # Calendar event within the cover window?
    cover_end = today + pd.Timedelta(days=min(days_cover, 60))
    upcoming = events[(pd.to_datetime(events["start_date"]) >= today)
                      & (pd.to_datetime(events["start_date"]) <= cover_end)]
    warn = ""
    if not upcoming.empty and days_cover < ORANGE * 2:
        warn = "⚠️ " + ", ".join(sorted(set(upcoming["event_name"])))

    rows.append({
        "Category": category,
        "Current stock": int(stock),
        "Predicted 30d demand": round(pred_30d, 1),
        "Mean daily demand": round(mean_daily, 2),
        "Days of cover": round(days_cover, 1),
        "Signal": signal,
        "Calendar risk": warn,
    })

df = pd.DataFrame(rows)
order = {"🔴 Reorder now": 0, "🟠 Watch": 1, "🟢 OK": 2}
df = df.sort_values(by="Signal", key=lambda s: s.map(order)).reset_index(drop=True)

c1, c2, c3 = st.columns(3)
c1.metric("🔴 Reorder now", int((df["Signal"].str.startswith("🔴")).sum()))
c2.metric("🟠 Watch", int((df["Signal"].str.startswith("🟠")).sum()))
c3.metric("🟢 OK", int((df["Signal"].str.startswith("🟢")).sum()))

st.dataframe(df, use_container_width=True, hide_index=True)
st.caption(f"Thresholds: 🔴 < {RED}d · 🟠 < {ORANGE}d · 🟢 otherwise (env-tunable). "
           "Calendar risk flags an event landing inside the cover window.")
