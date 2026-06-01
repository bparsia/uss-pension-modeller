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

_pages = [
    st.Page("pages/0_Bluffers_Guide.py", title="Bluffer's Guide"),
    # st.Page("pages/2_Introduction.py",   title="Introduction"),
    # st.Page("pages/3_CI_Basics.py",      title="CI Basics"),
    # st.Page("pages/4_Projections.py",    title="Projections"),
    # st.Page("pages/5_CI_Schemes.py",     title="CI Schemes"),
]
pg = st.navigation(_pages)
pg.run()
