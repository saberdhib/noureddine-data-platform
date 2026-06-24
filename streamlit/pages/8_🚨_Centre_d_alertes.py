"""Page 8 — Centre d'alertes (Bloc 4).

One operational cockpit that consolidates every red flag the platform can raise:
  * stock-out risk (days-of-cover < lead time),
  * dormant / over-stocked capital (cover far above lead time),
  * model drift & MAPE breaches (monitoring.model_metrics),
  * last pipeline run status (monitoring.pipeline_runs).
Business + monitoring signals side by side. Aggregates only, no PII.
"""
import pandas as pd
import streamlit as st

from lib import db, insights

st.set_page_config(page_title="Centre d'alertes", page_icon="🚨", layout="wide")
from lib import brand as _brand; _brand.apply()
st.title("🚨 Centre d'alertes")
st.caption("Vue unique de pilotage : ruptures, sur-stock, dérive du modèle et état des pipelines.")

LEAD_TIME = 21
today = db.data_today()

with st.spinner("Collecte des signaux…"):
    sig = insights.marketing_signals(today, LEAD_TIME)
    # monitoring (drift / mape / pipeline) — best-effort
    try:
        mm = db.run_query("""SELECT drift_score, mape, breached, measured_at
                             FROM monitoring.model_metrics ORDER BY measured_at DESC LIMIT 1""")
    except Exception:
        mm = pd.DataFrame()
    try:
        pr = db.run_query("""SELECT status, dag_id, created_at
                             FROM monitoring.pipeline_runs ORDER BY created_at DESC LIMIT 1""")
    except Exception:
        pr = pd.DataFrame()

cats = pd.DataFrame(sig["categories"])
ruptures = cats[(cats["jours_de_couverture"].notna())
                & (cats["jours_de_couverture"] < LEAD_TIME)] if not cats.empty else pd.DataFrame()
dormant = cats[cats["stock_dormant"]] if not cats.empty else pd.DataFrame()

# --- headline alert tiles ---
drift = float(mm.iloc[0]["drift_score"]) if not mm.empty else None
mape = float(mm.iloc[0]["mape"]) if not mm.empty else None
pipe = str(pr.iloc[0]["status"]) if not pr.empty else "—"

c1, c2, c3, c4 = st.columns(4)
c1.metric("🔴 Ruptures", len(ruptures))
c2.metric("🛑 Sur-stock (catégories)", len(dormant),
          help=f"Capital immobilisé : €{sig['valeur_stock_dormant_eur']:,.0f}")
c3.metric("📉 Drift / MAPE",
          f"{drift:.2f} / {mape:.0%}" if drift is not None else "—",
          delta="seuils 0.50 / 30%", delta_color="off")
c4.metric("🚦 Dernier pipeline", pipe)

st.divider()

def _alert(level: str, title: str, detail: str):
    icon = {"red": "🔴", "orange": "🟠", "green": "🟢"}[level]
    (st.error if level == "red" else st.warning if level == "orange" else st.success)(
        f"{icon} **{title}** — {detail}")

# --- consolidated alert feed ---
st.subheader("Alertes actives")
any_alert = False

if not ruptures.empty:
    any_alert = True
    for _, r in ruptures.iterrows():
        _alert("red", f"Rupture imminente — {r['categorie']}",
               f"{r['jours_de_couverture']} j de couverture < délai de réappro {LEAD_TIME} j. "
               f"Commander maintenant.")

if not dormant.empty:
    any_alert = True
    _alert("orange", "Capital immobilisé (sur-stock)",
           f"€{sig['valeur_stock_dormant_eur']:,.0f} dormants sur : "
           f"{', '.join(dormant['categorie'].tolist())}. Envisager déstockage / promo.")

if sig["categories_en_chute"]:
    any_alert = True
    _alert("orange", "Chute des ventes",
           f"Catégories en baisse (≥15% sur 14 j) : {', '.join(sig['categories_en_chute'])}.")

if drift is not None and drift >= 0.5:
    any_alert = True
    _alert("red", "Dérive du modèle (drift)", f"Score {drift:.2f} ≥ 0.50 → réentraînement requis.")
if mape is not None and mape >= 0.30:
    any_alert = True
    _alert("red", "Performance modèle (MAPE)", f"MAPE {mape:.0%} ≥ 30% → réentraînement requis.")
if pipe and pipe != "success" and pipe != "—":
    any_alert = True
    _alert("red", "Pipeline en échec", f"Dernier run : {pipe}.")

if not any_alert:
    st.success("🟢 Aucune alerte active — tout est nominal.")

# --- upcoming calendar context ---
with st.expander("📅 Événements calendrier (60 prochains jours)"):
    st.json(sig["evenements_a_venir"])

st.divider()
st.subheader("Détail par catégorie")
if not cats.empty:
    st.dataframe(
        cats.rename(columns={
            "categorie": "Catégorie", "stock_unites": "Stock (u)",
            "stock_valeur_eur": "Stock (€)", "tendance_14j_pct": "Tendance 14j %",
            "demande_prevue_30j": "Demande 30j", "jours_de_couverture": "Couverture (j)",
            "stock_dormant": "Sur-stock", "chute_ventes": "Chute",
        }),
        use_container_width=True, hide_index=True,
    )

st.caption("Cockpit d'aide à la décision — business (rupture/sur-stock) + MLOps (drift/MAPE/pipeline). "
           "Agrégats gouvernés, aucune PII.")
