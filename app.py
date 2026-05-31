"""USS Modeller — educational tool for USS conditional indexation."""
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="USS Modeller",
    page_icon=str(Path(__file__).parent / "branding" / "assets" / "ucuc-6.png"),
    layout="centered",
)

# Password gate — remove once app is public
_password = st.secrets.get("APP_PASSWORD", "")
if _password:
    if not st.session_state.get("authenticated"):
        pwd = st.text_input("Password", type="password")
        if pwd == _password:
            st.session_state["authenticated"] = True
            st.rerun()
        elif pwd:
            st.error("Incorrect password.")
        st.stop()

from branding.branding import apply_branding
apply_branding(page_title="USS Modeller")

st.title("USS Pension Modeller")
st.markdown(
    "An educational tool for understanding conditional indexation in the USS pension scheme. "
    "Use the pages in the sidebar to explore how different indexation schemes perform "
    "across a range of economic scenarios."
)

st.info(
    "**Start here:** Page 1 introduces pension indexation and why it matters. "
    "Later pages introduce conditional indexation and its variants."
)
