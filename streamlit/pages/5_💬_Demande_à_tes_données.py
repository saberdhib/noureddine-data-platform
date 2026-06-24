"""Page 5 — "Demande à tes données" (Bloc 4, optional LLM layer).

A natural-language chat grounded ONLY on aggregated gold metrics (KPIs, per-category
demand/stock, upcoming calendar events). No PII is ever sent (DPIA #2). The model is
told to answer strictly from the provided snapshot and to say when it doesn't know.
"""
import json

import streamlit as st

from lib import db, insights, llm

st.set_page_config(page_title="Demande à tes données", page_icon="💬", layout="wide")
st.title("💬 Demande à tes données")
st.caption("Pose une question métier en français — la réponse est calculée à partir des données "
           "agrégées du `gold` (CA, demande, stock, calendrier). Aucune donnée personnelle (DPIA #2).")

if not llm.is_enabled():
    st.info("🔑 Conseiller désactivé. Définis `OPENAI_API_KEY` dans `.env` puis relance Streamlit.")
    st.stop()

# --- build the grounding snapshot once per session (refreshable) ---
if "qa_overview" not in st.session_state or st.sidebar.button("🔄 Rafraîchir les données"):
    with st.spinner("Préparation du contexte (KPIs, stock, prévisions)…"):
        st.session_state.qa_overview = insights.data_overview(db.data_today())
        st.session_state.qa_history = []

overview = st.session_state.qa_overview
st.caption(f"Modèle : `{llm.OPENAI_MODEL}` · contexte : 90 j de KPIs + stock/demande par catégorie.")

with st.expander("📦 Contexte transmis au modèle (agrégé, sans PII)"):
    st.json(overview)

SYSTEM = (
    "Tu es analyste data pour NOUREDDINE, marque e-commerce premium de mode masculine dont la "
    "demande suit le calendrier islamique (Ramadan, Aïd al-Fitr, Aïd al-Adha, saison des mariages) "
    "et les pics retail (Black Friday). Réponds en français, de façon concise et chiffrée, en "
    "t'appuyant UNIQUEMENT sur le SNAPSHOT JSON fourni (données agrégées par catégorie, aucune "
    "donnée personnelle). Si l'information n'est pas dans le snapshot, dis-le clairement et ne "
    "l'invente pas. Voici le snapshot :\n\n" + json.dumps(overview, ensure_ascii=False)
)

# suggestion chips
st.write("**Exemples :**")
examples = [
    "Quelle catégorie porte le plus le chiffre d'affaires ?",
    "Quelles catégories risquent la rupture avant l'Aïd ?",
    "Où ai-je du stock dormant et combien ça représente en valeur ?",
    "Quelles ventes sont en chute et que recommander ?",
]
cols = st.columns(len(examples))
clicked = None
for c, ex in zip(cols, examples):
    if c.button(ex, use_container_width=True):
        clicked = ex

# render history
for m in st.session_state.get("qa_history", []):
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Pose ta question sur les données…") or clicked
if prompt:
    st.session_state.qa_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Analyse…"):
            try:
                answer = llm.chat(SYSTEM, prompt, max_tokens=700)
            except Exception as exc:
                answer = f"❌ Échec de l'appel au modèle : {exc}"
        st.markdown(answer)
    st.session_state.qa_history.append({"role": "assistant", "content": answer})

st.caption("Aide à la décision — les réponses s'appuient sur des agrégats gouvernés (aucune PII).")
