# utils/themes.py

import streamlit as st

def get_plotly_template(base: str | None = None) -> str:
    """
    Backward-compatible: works with get_plotly_template() and get_plotly_template(base).
    If base is None, try to read Streamlit theme base and map to a Plotly template.
    """
    if base is None:
        try:
            base = st.get_option("theme.base")
        except Exception:
            base = "dark"

    base = (base or "").lower()
    if base in ("dark", "night"):
        return "plotly_dark"
    return "plotly_white"
