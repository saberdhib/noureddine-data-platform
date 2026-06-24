"""NOUREDDINE brand theming for the Streamlit app (Bloc 4).

apply() injects the brand look (elegant serif wordmark + sand/charcoal palette) and,
if a real logo file is bundled at streamlit/assets/logo.{png,svg,jpg}, uses it via
st.logo(). Drop your wordmark there to replace the CSS wordmark.
"""
from __future__ import annotations

import os

import streamlit as st

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # streamlit/
_LOGO_CANDIDATES = [os.path.join(_HERE, "assets", n)
                    for n in ("logo.png", "logo.svg", "logo.jpg", "logo.jpeg")]

_CSS = """
<style>
:root { --nd-sand:#b89b72; --nd-ink:#1a1a1a; --nd-cream:#f6f1e9; }
/* elegant serif headings, brand palette */
h1, h2, h3 { font-family: 'Georgia','Times New Roman',serif !important; letter-spacing:.5px;
             color: var(--nd-ink); }
section[data-testid="stSidebar"] { background: var(--nd-cream); }
div[data-testid="stMetricValue"] { color: var(--nd-sand); }
.stButton > button[kind="primary"], .stDownloadButton > button {
    background: var(--nd-ink); border-color: var(--nd-ink); }
.nd-wordmark { font-family:'Georgia',serif; text-align:center; letter-spacing:8px;
    font-size:1.5rem; font-weight:600; color:var(--nd-ink); margin:.2rem 0 0 0; }
.nd-tag { text-align:center; letter-spacing:3px; font-size:.62rem; color:var(--nd-sand);
    margin:0 0 .6rem 0; }
.nd-rule { border:none; border-top:1px solid var(--nd-sand); opacity:.4; margin:.4rem 0 1rem 0; }
</style>
"""


def apply() -> None:
    """Call once at the top of each page (after st.set_page_config)."""
    st.markdown(_CSS, unsafe_allow_html=True)
    logo = next((p for p in _LOGO_CANDIDATES if os.path.exists(p)), None)
    if logo:
        try:
            st.logo(logo)
        except Exception:
            pass
    else:  # CSS wordmark in the sidebar when no logo file is bundled
        st.sidebar.markdown(
            '<div class="nd-wordmark">NOUREDDINE</div>'
            '<div class="nd-tag">DISCIPLINE · ÉLÉGANCE · INTENTION</div>'
            '<hr class="nd-rule"/>',
            unsafe_allow_html=True,
        )
