"""NOUREDDINE — Business app home (Bloc 4).

Decision-support front-end for stock & treasury planning. Business only — model
monitoring lives in Grafana/Evidently (separation of concerns). Forecasts come
from the FastAPI service; this app never loads the model directly.
"""
import streamlit as st

from lib import api_client

st.set_page_config(page_title="NOUREDDINE — Data Platform", page_icon="🧕", layout="wide")

st.title("🧕 NOUREDDINE — Data Platform")
st.caption("Bloc 4 · AI/MLOps · Demand forecasting & stock piloting against the Islamic cultural calendar")

st.markdown(
    """
Welcome to the **business consumption** layer of the NOUREDDINE Data Platform.

This app turns the governed warehouse (`gold`) and the LightGBM demand model into
day-to-day decisions for a premium D2C menswear brand whose demand is driven by
the **Islamic cultural calendar** (Ramadan, Eid al-Fitr, Eid al-Adha, Nikah
season) and retail peaks (Black Friday, Summer Sale).

### Pages
- **📊 Executive Dashboard** — revenue, orders, AOV, top categories & channels.
- **📈 Demand Forecast** — J-90 history + J+30 forecast with **calendar overlays**. ⭐
- **📦 Stock Pilot** — inventory vs predicted demand, days of cover, restock signals.

> Forecasts are served by the FastAPI model service. Monitoring (drift, MAPE) is
> in Grafana + Evidently, not here.
"""
)

with st.sidebar:
    st.header("Model")
    try:
        info = api_client.model_info()
        st.success("API reachable ✅")
        st.metric("Model version", info.get("version", "—"))
        mape = info.get("global_mape")
        st.metric("Global MAPE", f"{mape:.1%}" if isinstance(mape, (int, float)) else "—")
        st.caption(f"Trained at: {info.get('trained_at', '—')}")
        st.caption(f"Categories: {', '.join(info.get('categories', []))}")
    except Exception as exc:
        st.error("Forecast API not reachable.")
        st.caption(f"{exc}")
        st.caption("Start it with the `api` compose service (port 8000).")
