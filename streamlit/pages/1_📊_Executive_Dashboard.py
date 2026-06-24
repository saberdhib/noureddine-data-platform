"""Page 1 — Executive Dashboard (Bloc 4). KPIs from the gold layer."""
import json
from datetime import date, timedelta

import plotly.express as px
import streamlit as st

from lib import db, insights, llm

st.set_page_config(page_title="Executive Dashboard", page_icon="📊", layout="wide")
from lib import brand as _brand; _brand.apply()
st.title("📊 Executive Dashboard")
st.caption("Business KPIs from the governed `gold` star schema.")

# --- date range filter ---
today = date(2026, 6, 11)
default_start = today - timedelta(days=180)
col_a, col_b = st.columns(2)
start = col_a.date_input("From", value=default_start)
end = col_b.date_input("To", value=today)
start_s, end_s = start.isoformat(), end.isoformat()

k = db.kpis(start_s, end_s).iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"€{k['revenue']:,.0f}")
c2.metric("Orders", f"{int(k['orders']):,}")
c3.metric("Units sold", f"{int(k['units']):,}")
c4.metric("Avg order value", f"€{k['aov']:,.0f}")

st.divider()

left, right = st.columns([2, 1])
with left:
    st.subheader("Revenue over time")
    rev = db.revenue_by_day(start_s, end_s)
    if rev.empty:
        st.info("No data in the selected range.")
    else:
        fig = px.area(rev, x="date", y="revenue", labels={"revenue": "Revenue (€)", "date": ""})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top channels")
    ch = db.top_channels(start_s, end_s)
    if not ch.empty:
        fig = px.pie(ch, names="channel", values="revenue", hole=0.45)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Top categories")
cat = db.top_categories(start_s, end_s)
if not cat.empty:
    fig = px.bar(cat, x="category", y="revenue", color="category",
                 labels={"revenue": "Revenue (€)", "category": ""})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(cat, use_container_width=True, hide_index=True)

# --- AI executive summary (optional LLM layer; aggregates only, no PII) ---------
st.divider()
st.subheader("🪄 Résumé exécutif (IA)")
if not llm.is_enabled():
    st.info("🔑 Active la clé LLM (`OPENAI_API_KEY` dans `.env`) pour générer un résumé automatique.")
else:
    st.caption(f"Modèle : `{llm.OPENAI_MODEL}` · données agrégées uniquement (aucune PII).")
    if st.button("Générer le résumé exécutif", type="primary"):
        with st.spinner("Analyse des KPIs en cours…"):
            try:
                snap = insights.executive_snapshot(start_s, end_s)
                sys = (
                    "Tu es analyste business pour NOUREDDINE, marque e-commerce premium de mode "
                    "masculine (demande rythmée par le calendrier islamique : Ramadan, Aïd, saison "
                    "des mariages, + Black Friday). À partir UNIQUEMENT des chiffres agrégés fournis "
                    "(aucune donnée personnelle), rédige en français un résumé exécutif court : "
                    "1) **Synthèse** (2-3 phrases) ; 2) **Points clés** (catégories et canaux qui "
                    "portent le CA) ; 3) **À surveiller** (1-2 recommandations). N'invente aucun "
                    "chiffre, n'utilise que ceux fournis."
                )
                st.markdown(llm.chat(sys, json.dumps(snap, ensure_ascii=False)))
            except Exception as exc:
                st.error(f"Échec de l'appel au modèle : {exc}")
