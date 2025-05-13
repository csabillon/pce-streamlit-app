import streamlit as st
from datetime import datetime, timedelta

def render_sidebar():
    today = datetime.today()
    default_start = today - timedelta(days=30)
    default_end = today

    rigs = ["TransoceanDPS", "TransoceanDTH", "TransoceanDPT"]
    rig = st.sidebar.selectbox("Select Rig", rigs)
    start_date = st.sidebar.date_input("Start Date", default_start)
    end_date = st.sidebar.date_input("End Date", default_end)

    st.sidebar.markdown("### Ramp Detection Windows (seconds)")
    category_windows = {
        "Annular": st.sidebar.slider("Annular", 5, 60, 15),
        "Pipe Ram": st.sidebar.slider("Pipe Ram", 5, 90, 30),
        "Shear Ram": st.sidebar.slider("Shear Ram", 10, 120, 45),
        "Casing Shear": st.sidebar.slider("Casing Shear", 10, 150, 60),
        "Connector": st.sidebar.slider("Connector", 10, 180, 90),
    }

    return rig, start_date, end_date, category_windows
