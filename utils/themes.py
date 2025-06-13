#utils/themes.py

import streamlit as st

def get_plotly_template():
    theme = st._config.get_option("theme.base")
    return "plotly_dark" if theme == "dark" else "plotly_white"
