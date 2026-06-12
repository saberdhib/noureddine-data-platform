"""Page 1 — Executive Dashboard (Bloc 4). KPIs from the gold layer."""
from datetime import date, timedelta

import plotly.express as px
import streamlit as st

from lib import db

st.set_page_config(page_title="Executive Dashboard", page_icon="📊", layout="wide")
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
