"""Page 12 — Suivi du modèle (Bloc 4, read-only).

Tracks the model lifecycle and results from the monitoring tables (model_metrics,
retrain_events) — no pipeline change. Surfaces fairer metrics alongside MAPE (which
is inflated on low-volume, intermittent demand) and the retraining history.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from lib import api_client, brand as _brand, db

st.set_page_config(page_title="Suivi du modèle", page_icon="📉", layout="wide")
_brand.apply()
st.title("📉 Suivi du modèle (MLOps)")
st.caption("Cycle de vie et performance du modèle de prévision — lecture seule des tables de "
           "monitoring. Aucune donnée personnelle.")


@st.cache_data(ttl=60, show_spinner=False)
def _metrics():
    return db.run_query("""SELECT measured_at, model_version, drift_score, mape, rmse, breached
                           FROM monitoring.model_metrics ORDER BY measured_at""")


@st.cache_data(ttl=60, show_spinner=False)
def _events():
    return db.run_query("""SELECT occurred_at, model_version, current_mape, new_mape, promoted, reason
                           FROM monitoring.retrain_events ORDER BY occurred_at DESC""")


@st.cache_data(ttl=300, show_spinner=False)
def _mean_daily_demand():
    df = db.run_query("""
        WITH daily AS (
            SELECT p.category, d.date, COUNT(DISTINCT f.order_id) AS n
            FROM gold.fact_sales f
            JOIN gold.dim_date d ON d.date_key = f.date_key
            JOIN gold.dim_product p ON p.product_key = f.product_key
            GROUP BY 1, 2)
        SELECT AVG(n) AS mean_daily FROM daily""")
    return float(df.iloc[0]["mean_daily"]) if not df.empty else None


mm = _metrics()
ev = _events()
try:
    info = api_client.model_info()
except Exception:
    info = {}

if mm.empty:
    st.info("Aucune métrique encore. Lance `monitor_model` (et `retrain_model`) dans Airflow.")
    st.stop()

last = mm.iloc[-1]
mape = float(last["mape"]) if pd.notna(last["mape"]) else None
rmse = float(last["rmse"]) if pd.notna(last["rmse"]) else None
drift = float(last["drift_score"]) if pd.notna(last["drift_score"]) else None
mean_demand = _mean_daily_demand()
nrmse = (rmse / mean_demand) if (rmse and mean_demand) else None
n_promo = int(ev["promoted"].sum()) if not ev.empty else 0

# --- result cards ---
st.subheader("Résultat du modèle actif")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Version active", info.get("version", last["model_version"]))
c2.metric("RMSE (erreur absolue)", f"{rmse:.1f}" if rmse else "—",
          help="Erreur moyenne en nombre de commandes/jour — la mesure la plus interprétable.")
c3.metric("RMSE normalisé", f"{nrmse:.0%}" if nrmse else "—",
          help=f"RMSE / demande moyenne ({mean_demand:.1f}/j) — % plus juste que le MAPE.")
c4.metric("MAPE", f"{mape:.0%}" if mape else "—", delta="⚠️ gonflé (faibles volumes)",
          delta_color="off")

c5, c6, c7 = st.columns(3)
c5.metric("Drift (dérive)", f"{drift:.2f}" if drift is not None else "—",
          delta="seuil 0.50", delta_color="off")
c6.metric("Entraînements", len(ev))
c7.metric("Modèles promus", n_promo)

with st.expander("ℹ️ Pourquoi le MAPE est-il élevé ? (à dire au jury)"):
    st.markdown(
        "Le **MAPE divise par le réel** : sur une demande **faible et intermittente** "
        "(beaucoup de jours à ≤3 commandes pour GiftSet / Leather Goods), un petit écart "
        "devient un % énorme (réel=1, prévu=4 → 300%). Il **diverge** sur les petites "
        "valeurs et est indéfini à 0.\n\n"
        "➡️ Mesures plus justes : le **RMSE** (erreur absolue, ~±commandes/jour) et le "
        "**RMSE normalisé**. Le modèle capte la structure calendaire ; le MAPE est un "
        "**artefact de métrique** sur la demande sparse, pas un échec du modèle."
    )

st.divider()

# --- training history ---
st.subheader("Historique des entraînements")
if not ev.empty:
    e = ev.copy()
    e["statut"] = e["promoted"].map({True: "✅ promu", False: "⏸️ conservé"})
    st.dataframe(
        e[["occurred_at", "model_version", "current_mape", "new_mape", "statut", "reason"]]
        .rename(columns={"occurred_at": "Date", "model_version": "Version",
                         "current_mape": "MAPE courant", "new_mape": "MAPE candidat",
                         "reason": "Raison"}),
        use_container_width=True, hide_index=True,
    )

# --- metrics over time ---
st.subheader("Évolution des métriques")
g1, g2 = st.columns(2)
with g1:
    fig = px.line(mm, x="measured_at", y="rmse", markers=True, labels={"rmse": "RMSE", "measured_at": ""})
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), title="RMSE dans le temps")
    st.plotly_chart(fig, use_container_width=True)
with g2:
    fig = px.line(mm, x="measured_at", y="drift_score", markers=True,
                  labels={"drift_score": "Drift", "measured_at": ""})
    fig.add_hline(y=0.5, line_dash="dash", line_color="red")
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), title="Drift dans le temps")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Suivi MLOps en lecture seule (monitoring.model_metrics + retrain_events). "
           "Le monitoring complet reste dans Grafana ; cette vue résume le cycle du modèle.")
