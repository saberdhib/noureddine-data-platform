"""Page 10 — Studio Marketing IA (Bloc 4, optional generative layer).

Pipeline créatif : choisir une image source (galerie marque / upload / génération
texte→image) → la décliner en variantes (image→image) → l'animer en clip social
(image→vidéo). Via HF Inference Providers (fal-ai), facturé sur l'org (HF_BILL_TO).
Contenu marketing uniquement — aucune donnée client.
"""
import streamlit as st

from lib import assets, brand as _brand, db, studio

st.set_page_config(page_title="Studio Marketing", page_icon="🎨", layout="wide")
_brand.apply()
st.title("🎨 Studio Marketing IA")
st.caption("Génère et décline des visuels de campagne, puis anime-les en clips sociaux. "
           "Contenu marketing uniquement — aucune donnée client.")

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


def _set_img(data: bytes, label: str):
    st.session_state.studio_img = data
    st.session_state.studio_img_label = label


# ===========================================================================
# 1) Image source : galerie / upload / génération
# ===========================================================================
st.subheader("1 · Choisir l'image source")
mode = st.radio("Source", ["🖼️ Galerie marque", "⬆️ Téléverser", "✨ Générer (texte→image)"],
                horizontal=True, label_visibility="collapsed")

if mode == "🖼️ Galerie marque":
    try:
        names = assets.list_images()
    except Exception as exc:
        names = []
        st.error(f"MinIO injoignable : {exc}")
    if not names:
        st.info("Aucune image dans le bucket `brand`. Upload : `bash infra/scripts/upload-brand.sh`.")
    else:
        pick = st.selectbox("Visuel de la galerie", names)
        if st.button("Utiliser ce visuel"):
            _set_img(assets.get_object(pick), f"galerie · {pick}")

elif mode == "⬆️ Téléverser":
    up = st.file_uploader("Image (PNG/JPG)", type=["png", "jpg", "jpeg", "webp"])
    if up is not None:
        _set_img(up.read(), f"upload · {up.name}")

else:  # génération texte→image
    c1, c2, c3 = st.columns(3)
    category = c1.selectbox("Catégorie", cats)
    event = c2.selectbox("Événement", events)
    style = c3.text_input("Style (optionnel)", placeholder="ex. tons sable, ambiance nocturne")
    prompt = studio.campaign_prompt(category, event, style)
    with st.expander("📝 Prompt"):
        st.code(prompt, language="text")
    st.caption(f"Modèle image : `{studio.TXT2IMG_MODEL}`")
    if st.button("✨ Générer le visuel", type="primary"):
        with st.spinner("Génération…"):
            try:
                _set_img(studio.text_to_image(prompt), f"généré · {category}/{event}")
            except Exception as exc:
                st.error(f"Échec génération : {exc}")

img = st.session_state.get("studio_img")
if img:
    st.image(img, caption=f"Image active — {st.session_state.get('studio_img_label','')}",
             use_container_width=True)
    st.download_button("⬇️ Télécharger l'image active", img,
                       file_name="noureddine_visuel.png", mime="image/png")

st.divider()

# ===========================================================================
# 2) Décliner (image → image)
# ===========================================================================
st.subheader("2 · Décliner l'image (image→image)")
st.caption(f"Modèle : `{studio.EDIT_MODEL}` · crée des variantes À PARTIR de l'image active.")
if not img:
    st.info("Choisis d'abord une image source ci-dessus.")
else:
    edit = st.text_input("Que modifier / décliner ?",
                         value="même style premium, autre pose élégante, fond épuré, lumière douce")
    if st.button("🎭 Générer une variante", type="primary"):
        with st.spinner("Déclinaison…"):
            try:
                var = studio.image_to_image(img, edit)
                _set_img(var, "variante")
                st.image(var, caption="Nouvelle variante (devient l'image active)",
                         use_container_width=True)
                st.download_button("⬇️ Télécharger la variante", var,
                                   file_name="noureddine_variante.png", mime="image/png",
                                   key="dl_var")
            except Exception as exc:
                st.error(f"Échec déclinaison : {exc}")

st.divider()

# ===========================================================================
# 3) Animer (image → vidéo)
# ===========================================================================
st.subheader("3 · Animer en clip social (image→vidéo)")
st.caption(f"Modèle : `{studio.IMG2VID_MODEL}` · ⏳ plus lent et plus coûteux. Anime l'image active.")
if not img:
    st.info("Choisis / génère une image d'abord.")
else:
    motion = st.text_input("Mouvement / animation",
                           value="slow elegant camera pan, fabric gently moving in the breeze")
    if st.button("🎬 Générer le clip (coûteux)", type="secondary"):
        with st.spinner("Génération vidéo (1-2 min)…"):
            try:
                video = studio.image_to_video(st.session_state.studio_img, motion)
                st.video(video)
                st.download_button("⬇️ Télécharger le clip", video,
                                   file_name="noureddine_clip.mp4", mime="video/mp4", key="dl_vid")
            except Exception as exc:
                st.error(f"Échec génération vidéo : {exc}")

st.caption("Couche générative optionnelle — contenu marketing, aucune PII. Source → déclinaison → "
           "animation, pour des campagnes social/CRM alignées sur le calendrier culturel.")
