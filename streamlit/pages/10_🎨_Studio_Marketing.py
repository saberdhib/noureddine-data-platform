"""Page 10 — Studio Marketing IA (Bloc 4, optional generative layer).

Generate campaign visuals (text-to-image) and short social clips (image-to-video) for
NOUREDDINE, themed on the Islamic calendar. Uses the HF Inference Providers (fal-ai).
Marketing content only — no customer data / no PII. Image & especially video generation
cost more than text; an org spending limit is recommended.
"""
import streamlit as st

from lib import db, studio

st.set_page_config(page_title="Studio Marketing", page_icon="🎨", layout="wide")
st.title("🎨 Studio Marketing IA")
st.caption("Génère des visuels de campagne et des clips sociaux (Instagram/TikTok) calés sur le "
           "calendrier. Contenu marketing uniquement — aucune donnée client.")

if not studio.is_enabled():
    st.info("🔑 Active la clé HF (`OPENAI_API_KEY` dans `.env`) pour le studio génératif.")
    st.stop()

st.warning("💸 La génération d'images et **surtout de vidéos** consomme du crédit HF Inference "
           "Providers (facturé sur l'org). Garde une limite de dépense sur l'org.")

try:
    cats = db.categories()
except Exception:
    cats = ["Ready-to-Wear", "Grooming", "Accessories", "Leather Goods", "GiftSet"]
events = ["Évergreen", "Ramadan", "Aïd al-Fitr", "Aïd al-Adha", "Saison des mariages", "Black Friday"]

# ---------------------------------------------------------------------------
# 1) Visuel de campagne (text-to-image)
# ---------------------------------------------------------------------------
st.subheader("1 · Visuel de campagne (text-to-image)")
c1, c2, c3 = st.columns(3)
category = c1.selectbox("Catégorie", cats)
event = c2.selectbox("Événement", events)
style = c3.text_input("Style (optionnel)", placeholder="ex. tons sable, ambiance Ramadan nocturne")

prompt = studio.campaign_prompt(category, event, style)
with st.expander("📝 Prompt envoyé au modèle"):
    st.code(prompt, language="text")
st.caption(f"Modèle image : `{studio.TXT2IMG_MODEL}`")

if st.button("🎨 Générer le visuel", type="primary"):
    with st.spinner("Génération de l'image…"):
        try:
            st.session_state.studio_img = studio.text_to_image(prompt)
        except Exception as exc:
            st.error(f"Échec génération image : {exc}")

if st.session_state.get("studio_img"):
    st.image(st.session_state.studio_img, caption=f"{category} · {event}", use_container_width=True)
    st.download_button("⬇️ Télécharger le visuel (PNG)", st.session_state.studio_img,
                       file_name="noureddine_campagne.png", mime="image/png")

st.divider()

# ---------------------------------------------------------------------------
# 2) Clip social (image-to-video) — optionnel, coûteux
# ---------------------------------------------------------------------------
st.subheader("2 · Clip social (image-to-video)")
st.caption(f"Modèle vidéo : `{studio.IMG2VID_MODEL}` · ⏳ plus lent et plus coûteux.")
if not st.session_state.get("studio_img"):
    st.info("Génère d'abord un visuel ci-dessus — il servira d'image de départ pour la vidéo.")
else:
    motion = st.text_input("Mouvement / animation",
                           value="slow elegant camera pan, fabric gently moving in the breeze")
    if st.button("🎬 Générer le clip (coûteux)", type="secondary"):
        with st.spinner("Génération de la vidéo (peut prendre 1-2 min)…"):
            try:
                video = studio.image_to_video(st.session_state.studio_img, motion)
                st.video(video)
                st.download_button("⬇️ Télécharger le clip", video,
                                   file_name="noureddine_clip.mp4", mime="video/mp4")
            except Exception as exc:
                st.error(f"Échec génération vidéo : {exc}")

st.caption("Couche générative optionnelle — contenu marketing, aucune PII. Pour les campagnes "
           "social/CRM (Instagram, TikTok) alignées sur le calendrier culturel.")
