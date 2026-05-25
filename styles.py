"""Shared styles and UI helpers for ussmodeller."""
import streamlit as st


def placeholder(text: str) -> None:
    """Render placeholder editorial text in a visually distinct callout.

    All text inside placeholder() calls is temporary — to be replaced by
    user-written commentary before publication.
    """
    st.info(f"✏️ **[Placeholder text — to be replaced]**\n\n{text}")
