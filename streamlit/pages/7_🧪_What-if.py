"""Page 7 — What-if / Simulateur (Bloc 4).

Move two levers — restock lead time and a promo demand uplift — and see live how
days-of-cover and stock-out risk change per category. Forecasts come from the
FastAPI service; inventory from the gold/oltp aggregates. No PII.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from lib import api_client, db

st.set_page_config(page_title="What-if", page_icon="🧪", layout="wide")
from lib import brand as _brand; _brand.apply()
st.title("🧪 What-if — Simulateur de pilotage")
st.caption("Ajuste le délai de réappro et un coup de pouce promo, et observe l'impact sur la "
           "couverture et le risque de rupture par catégorie. Prévisions via l'API, agrégats only.")

today = db.data_today()

with st.sidebar:
    st.header("Leviers")
    lead_time = st.slider("Délai de réapprovisionnement (jours)", 1, 60, 21)
    uplift = st.slider("Coup de pouce promo / demande (%)", -50, 100, 0,
                       help="Simule l'effet d'une promo (demande +X%) ou d'un creux (-X%).")
    horizon = 30

inv = db.inventory_by_category()
if inv.empty:
    st.error("Aucun inventaire — lance le simulateur + ingest_orders.")
    st.stop()

rows = []
for _, r in inv.iterrows():
    cat, stock = r["category"], float(r["stock"])
    try:
        fc = api_client.predict(cat, horizon)
    except Exception as exc:
        st.error(f"API de prévision injoignable : {exc}")
        st.stop()
    base_daily = max(0.01, float(fc["prediction"].mean()))
    adj_daily = max(0.01, base_daily * (1 + uplift / 100.0))
    cover_base = round(stock / base_daily, 1)
    cover_adj = round(stock / adj_daily, 1)
    rupture = cover_adj < lead_time
    rows.append({
        "Catégorie": cat,
        "Stock (u)": int(stock),
        "Demande/j (base)": round(base_daily, 1),
        "Demande/j (simulée)": round(adj_daily, 1),
        "Couverture (j)": cover_adj,
        "Couverture base (j)": cover_base,
        "Délai (j)": lead_time,
        "Risque": "🔴 Rupture" if rupture else ("🟠 Tendu" if cover_adj < lead_time * 1.5 else "🟢 OK"),
    })

df = pd.DataFrame(rows).sort_values("Couverture (j)").reset_index(drop=True)

n_rupture = int((df["Risque"].str.startswith("🔴")).sum())
n_watch = int((df["Risque"].str.startswith("🟠")).sum())
c1, c2, c3 = st.columns(3)
c1.metric("🔴 Ruptures simulées", n_rupture)
c2.metric("🟠 Tendu", n_watch)
c3.metric("Scénario", f"délai {lead_time} j · demande {uplift:+d}%")

fig = px.bar(df, x="Catégorie", y="Couverture (j)", color="Risque",
             color_discrete_map={"🔴 Rupture": "#d62728", "🟠 Tendu": "#ff7f0e", "🟢 OK": "#2ca02c"},
             labels={"Couverture (j)": "Jours de couverture (simulée)"})
fig.add_hline(y=lead_time, line_dash="dash", line_color="white",
              annotation_text=f"Délai de réappro ({lead_time} j)", annotation_position="top left")
fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df, use_container_width=True, hide_index=True)
st.caption("Sous la ligne pointillée = la couverture ne couvre pas le délai de réappro → rupture "
           "avant l'arrivée de la commande. Aide à la décision (human-in-the-loop).")
