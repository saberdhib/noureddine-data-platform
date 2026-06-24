"""Page 11 — Galerie marque (Bloc 4) — Digital Asset Manager.

Displays the brand/marketing media stored in the MinIO 'brand' bucket (logo, campaign
visuals, lookbook, product & accessory shots). Read-only; marketing content (no PII).
Upload assets with: bash infra/scripts/upload-brand.sh
"""
import streamlit as st

from lib import assets

st.set_page_config(page_title="Galerie marque", page_icon="🖼️", layout="wide")
from lib import brand as _brand; _brand.apply()
st.title("🖼️ Galerie marque (Digital Asset Manager)")
st.caption("Médias marketing gouvernés dans le data lake (bucket MinIO `brand`) : logo, visuels "
           "de campagne, lookbook, packshots. Contenu marketing — aucune donnée client.")

if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()


@st.cache_data(ttl=120, show_spinner=False)
def _list():
    return assets.list_images()


@st.cache_data(ttl=600, show_spinner=False)
def _img(name: str) -> bytes:
    return assets.get_object(name)


try:
    names = _list()
except Exception as exc:
    st.error(f"MinIO injoignable : {exc}")
    st.stop()

if not names:
    st.info("📭 Aucun asset dans le bucket `brand` pour l'instant.\n\n"
            "**Pour en ajouter :**\n"
            "1. Dépose tes images dans `~/noureddine-data-platform/brand-assets/`\n"
            "2. Lance `bash infra/scripts/upload-brand.sh`\n"
            "3. Reviens ici et clique 🔄 Rafraîchir.")
    st.stop()

st.metric("Visuels dans la galerie", len(names))
cols = st.columns(3)
for i, name in enumerate(names):
    with cols[i % 3]:
        try:
            data = _img(name)
            st.image(data, caption=name, use_container_width=True)
            st.download_button("⬇️", data, file_name=name.split("/")[-1],
                               key=f"dl_{i}", help="Télécharger")
        except Exception as exc:
            st.warning(f"{name}: {exc}")

st.caption("Stockage objet S3-compatible (MinIO) — mêmes principes qu'un AWS S3 en production. "
           "Les médias marketing vivent dans le lac, à côté des couches bronze/silver/gold.")
