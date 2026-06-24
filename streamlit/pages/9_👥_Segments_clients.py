"""Page 9 — Segments clients (Bloc 4) — RFM + KMeans clustering.

"Connaître nos clients" : segments customers from their behaviour (Recency, Frequency,
Monetary, basket, discount sensitivity, tenure) with KMeans, then lets the LLM name &
describe each segment and suggest a CRM action. Pseudonymised keys only; the LLM sees
only aggregate segment profiles (no PII).
"""
import json

import plotly.express as px
import streamlit as st

from lib import db, llm, segments

st.set_page_config(page_title="Segments clients", page_icon="👥", layout="wide")
from lib import brand as _brand; _brand.apply()
st.title("👥 Segments clients (RFM + clustering)")
st.caption("Segmentation comportementale des clients (Récence, Fréquence, Montant, panier, promo, "
           "ancienneté) par KMeans. Clés pseudonymisées ; l'IA ne voit que des profils agrégés.")

with st.sidebar:
    st.header("Paramètres")
    k = st.slider("Nombre de segments (k)", 2, 6, 4)

today = db.data_today()
with st.spinner("Calcul des features RFM…"):
    feats = segments.customer_features(today)

if feats.empty or len(feats) < k:
    st.error("Pas assez de clients pour segmenter. Lance le simulateur + ingest_orders "
             "(base clients réaliste requise).")
    st.stop()

df = segments.cluster(feats, k=k)
prof = segments.profiles(df)

st.metric("Clients segmentés", f"{len(df):,}")

c1, c2 = st.columns([3, 2])
with c1:
    st.subheader("Carte des clients (Fréquence × Valeur)")
    fig = px.scatter(
        df, x="frequency", y="monetary", color=df["segment"].astype(str),
        size="aov", hover_data=["recency_days", "discount_rate"],
        labels={"frequency": "Fréquence (commandes)", "monetary": "Valeur totale (€)",
                "color": "Segment"},
    )
    fig.update_layout(height=440, margin=dict(l=10, r=10, t=10, b=10), legend_title="Segment")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.subheader("Profil des segments")
    st.dataframe(prof, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🪄 Profils & actions CRM (IA)")
if not llm.is_enabled():
    st.info("🔑 Active la clé LLM (`OPENAI_API_KEY` dans `.env`) pour nommer les segments.")
else:
    st.caption(f"Modèle : `{llm.OPENAI_MODEL}` · profils agrégés uniquement (aucune PII).")
    if st.button("Nommer & décrire les segments", type="primary"):
        with st.spinner("Analyse des segments…"):
            try:
                sys = (
                    "Tu es responsable CRM pour NOUREDDINE, marque e-commerce premium de mode "
                    "masculine (diaspora musulmane occidentale ; demande rythmée par Ramadan, Aïd, "
                    "saison des mariages). On te fournit des PROFILS DE SEGMENTS clients agrégés "
                    "(aucune donnée personnelle) issus d'un clustering RFM. Pour CHAQUE segment, "
                    "donne en français : un **nom parlant** (ex. 'VIP fidèles', 'Occasionnels "
                    "sensibles aux promos', 'Nouveaux à fort potentiel', 'À risque/dormants'), une "
                    "**description** en 1-2 phrases (récence/fréquence/valeur/promo), et **1 action "
                    "CRM** concrète (offre, canal, timing calendaire). Appuie-toi sur les chiffres "
                    "fournis, n'en invente aucun. Format : un bloc par segment."
                )
                payload = {"nb_clients_total": int(len(df)),
                           "segments": json.loads(prof.to_json(orient="records"))}
                st.markdown(llm.chat(sys, json.dumps(payload, ensure_ascii=False), max_tokens=1100))
            except Exception as exc:
                st.error(f"Échec de l'appel au modèle : {exc}")

st.caption("Aide à la décision CRM — segmentation pseudonymisée, l'IA ne reçoit que des agrégats "
           "par segment (aucune PII). Cas d'usage distinct du forecasting (DPIA #2).")
