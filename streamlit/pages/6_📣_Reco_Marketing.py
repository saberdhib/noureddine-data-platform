"""Page 6 — Recommandations marketing (Bloc 4, optional LLM layer).

Spots two business risks from aggregated gold/inventory data and asks the LLM for
marketing actions:
  * sales drop  — categories whose recent 14-day demand fell sharply,
  * dormant stock — categories over-stocked in VALUE (cover far above lead time).
Aggregates only, no PII (DPIA #2). The model proposes; the human decides.
"""
import json

import pandas as pd
import streamlit as st

from lib import db, insights, llm

st.set_page_config(page_title="Reco Marketing", page_icon="📣", layout="wide")
st.title("📣 Recommandations marketing")
st.caption("Détecte les chutes de ventes et le stock dormant (en valeur), puis propose des actions "
           "marketing calées sur le calendrier. Données agrégées par catégorie, aucune PII.")

LEAD_TIME = 21
today = db.data_today()

with st.spinner("Calcul des signaux (ventes, stock, prévisions)…"):
    try:
        signals = insights.marketing_signals(today, LEAD_TIME)
    except Exception as exc:
        st.error(f"Impossible de calculer les signaux : {exc}")
        st.stop()

df = pd.DataFrame(signals["categories"])

c1, c2, c3 = st.columns(3)
c1.metric("💸 Valeur stock dormant", f"€{signals['valeur_stock_dormant_eur']:,.0f}")
c2.metric("📉 Catégories en chute", len(signals["categories_en_chute"]))
c3.metric("🛑 Catégories stock dormant", len(signals["categories_stock_dormant"]))

st.subheader("Signaux par catégorie")
st.dataframe(
    df.rename(columns={
        "categorie": "Catégorie", "stock_unites": "Stock (u)",
        "stock_valeur_eur": "Stock (€)", "tendance_14j_pct": "Tendance 14j %",
        "demande_prevue_30j": "Demande 30j", "jours_de_couverture": "Couverture (j)",
        "stock_dormant": "Dormant", "chute_ventes": "Chute",
    }),
    use_container_width=True, hide_index=True,
)

with st.expander("📅 Événements calendrier (60 prochains jours)"):
    st.json(signals["evenements_a_venir"])

st.divider()
st.subheader("🪄 Recommandations marketing (IA)")
if not llm.is_enabled():
    st.info("🔑 Active la clé LLM (`OPENAI_API_KEY` dans `.env`) pour générer les recommandations.")
else:
    st.caption(f"Modèle : `{llm.OPENAI_MODEL}` · aucune donnée personnelle envoyée.")
    if st.button("Générer les recommandations marketing", type="primary"):
        with st.spinner("Génération…"):
            try:
                sys = (
                    "Tu es responsable marketing/CRM pour NOUREDDINE, marque e-commerce premium de "
                    "mode masculine (clientèle de la diaspora musulmane occidentale). La demande est "
                    "rythmée par le calendrier islamique (Ramadan, Aïd al-Fitr, Aïd al-Adha, saison "
                    "des mariages) et les pics retail (Black Friday). À partir UNIQUEMENT des signaux "
                    "agrégés fournis (aucune donnée personnelle), propose un plan marketing actionnable "
                    "en français :\n"
                    "1. **Stock dormant** : pour les catégories sur-stockées en valeur, propose des "
                    "leviers de déstockage (promotion ciblée, bundle/gift set, mise en avant, timing "
                    "vs prochain événement calendaire) pour libérer la valeur immobilisée.\n"
                    "2. **Chute de ventes** : pour les catégories en baisse, propose des actions de "
                    "relance (campagne acquisition/retargeting par canal, offre, contenu).\n"
                    "3. **Opportunités calendaires** : aligne les actions sur les événements à venir.\n"
                    "Sois concret et priorisé. Cite les chiffres fournis (valeur €, tendance %, "
                    "couverture), n'en invente aucun."
                )
                reco = llm.chat(sys, json.dumps(signals, ensure_ascii=False), max_tokens=1100)
                st.markdown(reco)
            except Exception as exc:
                st.error(f"Échec de l'appel au modèle : {exc}")

st.caption("Aide à la décision (human-in-the-loop) — propositions à valider. Agrégats gouvernés, "
           "aucune PII (DPIA #2).")
