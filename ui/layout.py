import streamlit as st
from datetime import datetime, timedelta

def render_sidebar(default_rig: str | None = None):
    """
    Renders the rig selector, dates, and sliders.
    If default_rig matches one of our rig names, it will be pre-selected.
    """
    today = datetime.today()
    default_start = today - timedelta(days=60)
    default_end   = today

    # Our three allowable rigs
    rigs = ["TransoceanDPS", "TransoceanDTH", "TransoceanDPT"]

    # Key for our rig‐selectbox in session_state
    selectbox_key = "sidebar_selected_rig"

    # If the URL passed us a default_rig, force it into session_state
    if default_rig in rigs:
        st.session_state[selectbox_key] = default_rig
        default_index = rigs.index(default_rig)
    else:
        default_index = 0

    # Now render the selectbox with that key
    rig = st.sidebar.selectbox(
        "Select Rig",
        rigs,
        index=default_index,
        key=selectbox_key,
    )

    start_date = st.sidebar.date_input("Start Date", default_start)
    end_date   = st.sidebar.date_input("End Date", default_end)

    st.sidebar.markdown("### Ramp Detection Window (seconds)")
    category_windows = {
        "Annular":      st.sidebar.slider("Annular",      5,  60,  30),
        "Pipe Ram":     st.sidebar.slider("Pipe Ram",     5,  90,  60),
        "Shear Ram":    st.sidebar.slider("Shear Ram",   10, 120,  90),
        "Casing Shear": st.sidebar.slider("Casing Shear",10, 180, 120),
        "Connector":    st.sidebar.slider("Connector",   10, 180, 120),
    }

    if end_date < start_date:
        st.sidebar.error("End Date must be on or after Start Date")

    return rig, start_date, end_date, category_windows
