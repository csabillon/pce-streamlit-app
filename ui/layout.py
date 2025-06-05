import streamlit as st
from datetime import datetime, timedelta

def render_sidebar(default_rig: str | None = None):
    today = datetime.today()
    default_start = today - timedelta(days=60)
    default_end = today

    rigs = ["TransoceanDPS", "TransoceanDTH", "TransoceanDPT"]
    selectbox_key = "sidebar_selected_rig"

    # Do NOT directly assign session state here to avoid widget warning
    default_index = rigs.index(default_rig) if default_rig in rigs else 0

    rig = st.sidebar.selectbox(
        "Select Rig",
        rigs,
        index=default_index,
        key=selectbox_key,
    )

    start_date = st.sidebar.date_input("Start Date", default_start)
    end_date = st.sidebar.date_input("End Date", default_end)

    st.sidebar.markdown("### Ramp Detection Window (seconds)")
    category_windows = {
        "Annular": st.sidebar.slider("Annular", 5, 60, 30),
        "Pipe Ram": st.sidebar.slider("Pipe Ram", 5, 90, 60),
        "Shear Ram": st.sidebar.slider("Shear Ram", 10, 120, 90),
        "Casing Shear": st.sidebar.slider("Casing Shear", 10, 180, 120),
        "Connector": st.sidebar.slider("Connector", 10, 180, 120),
    }

    if end_date < start_date:
        st.sidebar.error("End Date must be on or after Start Date")

    return rig, start_date, end_date, category_windows
