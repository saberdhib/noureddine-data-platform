"""Page 4 — AI Restock Advisor (Bloc 4, optional LLM layer).

Grounds an OpenAI model on the platform's own numbers (forecast + inventory +
days of cover + upcoming calendar events, per category) to produce an actionable
restock briefing. Optional: needs OPENAI_API_KEY; degrades gracefully otherwise.
Only category-level aggregates are sent (no PII — DPIA #2). See ADR 0015.
"""
import os

import pandas as pd
import streamlit as st

from lib import ai_advisor, api_client, db

st.set_page_config(page_title="AI Advisor", page_icon="🤖", layout="wide")
st.title("🤖 Conseiller IA — Réapprovisionnement")
st.caption("Briefing d'action généré à partir des prévisions + stock + calendrier (agrégés par "
           "catégorie, aucune donnée personnelle). Option — nécessite `OPENAI_API_KEY`.")

# Restock lead time: the days between placing an order and receiving stock. The
# core decision: if days-of-cover < lead time, you WILL stock out before delivery.
LEAD_TIME = int(os.getenv("RESTOCK_LEAD_TIME_DAYS", "21"))
COVER_TARGET_DAYS = 30
today = db.data_today()        # anchored on the data frontier (aligns with the model)

with st.sidebar:
    st.header("Paramètres")
    LEAD_TIME = st.slider("Délai de réapprovisionnement (jours)", 1, 60, LEAD_TIME)
    st.caption("Au‑delà de ce délai sans stock = rupture certaine.")
st.caption(f"📆 Date pivot (frontière des données) : **{today.date().isoformat()}** · "
           f"délai réappro : **{LEAD_TIME} j**")

# --- assemble the grounding data (same sources as Stock Pilot) ---
inv = db.inventory_by_category()
if inv.empty:
    st.error("Aucun inventaire dans oltp.inventory — lance le simulateur + ingest_orders d'abord.")
    st.stop()

events = db.calendar_events()
upcoming_all = events[(pd.to_datetime(events["start_date"]) >= today)
                      & (pd.to_datetime(events["start_date"]) <= today + pd.Timedelta(days=45))]

rows = []
for _, r in inv.iterrows():
    category, stock = r["category"], float(r["stock"])
    try:
        fc = api_client.predict(category, COVER_TARGET_DAYS)
    except Exception as exc:
        st.error(f"API de prévision injoignable : {exc}")
        st.stop()
    pred_30d = float(fc["prediction"].sum())
    mean_daily = max(0.01, pred_30d / max(1, len(fc)))
    days_cover = round(stock / mean_daily, 1)
    # Decision factors the lead time: rupture if cover can't span the delivery delay.
    rupture_avant_livraison = days_cover < LEAD_TIME
    if rupture_avant_livraison:
        signal = "🔴 commander maintenant"
    elif days_cover < LEAD_TIME * 1.5:
        signal = "🟠 à commander bientôt"
    else:
        signal = "🟢 OK"
    # Reorder enough to cover the lead time + the next 30-day cycle.
    suggested = max(0, round(mean_daily * (LEAD_TIME + COVER_TARGET_DAYS) - stock))
    ev = [{"evenement": e["event_name"],
           "jours_avant": int((pd.Timestamp(e["start_date"]) - today).days)}
          for _, e in upcoming_all.iterrows()]
    rows.append({
        "categorie": category,
        "stock_actuel": int(stock),
        "demande_prevue_30j": round(pred_30d, 1),
        "demande_moy_jour": round(mean_daily, 2),
        "jours_de_couverture": days_cover,
        "lead_time_days": LEAD_TIME,
        "rupture_avant_livraison": bool(rupture_avant_livraison),
        "signal": signal,
        "suggested_reorder_units": int(suggested),
        "evenements_a_venir": ev,
    })

df = pd.DataFrame(rows).sort_values("jours_de_couverture").reset_index(drop=True)

# --- urgency KPIs ---
n_rupture = int(df["rupture_avant_livraison"].sum())
n_watch = int((df["signal"].str.startswith("🟠")).sum())
c1, c2, c3 = st.columns(3)
c1.metric("🔴 Rupture avant livraison", n_rupture, help="Couverture < délai de réappro")
c2.metric("🟠 À commander bientôt", n_watch)
c3.metric("🟢 OK", int((df["signal"].str.startswith("🟢")).sum()))

# --- the grounding table (useful even without an API key) ---
st.subheader("Données (ce que voit le conseiller)")
st.dataframe(
    df.drop(columns=["evenements_a_venir"]),
    use_container_width=True, hide_index=True,
)
with st.expander("📅 Événements calendrier pris en compte (45 prochains jours)"):
    if upcoming_all.empty:
        st.write("Aucun événement dans les 45 prochains jours.")
    else:
        st.dataframe(upcoming_all[["event_name", "event_type", "start_date", "end_date"]],
                     use_container_width=True, hide_index=True)

st.divider()

# --- the LLM briefing ---
if not ai_advisor.is_enabled():
    st.info("🔑 Conseiller IA désactivé. Définis `OPENAI_API_KEY` (et `OPENAI_MODEL`, défaut "
            "`gpt-4o-mini`) dans `.env` puis relance le service Streamlit pour l'activer. "
            "Les données ci-dessus restent disponibles sans clé.")
else:
    st.caption(f"Modèle : `{ai_advisor.OPENAI_MODEL}`")
    if st.button("🧠 Générer le briefing de réapprovisionnement", type="primary"):
        with st.spinner("Analyse en cours…"):
            try:
                briefing = ai_advisor.generate_briefing(rows, today.date().isoformat())
                st.markdown(briefing)
            except ai_advisor.AdvisorNotConfigured:
                st.warning("OPENAI_API_KEY non défini.")
            except Exception as exc:
                st.error(f"Échec de l'appel au modèle : {exc}")

st.caption("Aide à la décision (human-in-the-loop) — le conseiller propose, l'humain valide. "
           "Aucune donnée personnelle n'est envoyée (DPIA #2). Couche optionnelle — ADR 0015.")
