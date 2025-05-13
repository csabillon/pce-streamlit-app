# app.py

import streamlit as st
from datetime import timedelta

from config              import (
    CDF_PROJECT, CDF_CLUSTER,
    CDF_TENANT_ID, CDF_CLIENT_ID,
    CDF_CLIENT_SECRET,
)
from utils.themes        import get_plotly_template
from ui.layout           import render_sidebar
from logic.dashboard_data import load_dashboard_data
from ui.dashboard        import render_dashboard

# ────────── Page config & border CSS ──────────────────────────────────────
st.set_page_config(page_title="BOP Valve Dashboard", layout="wide")
st.markdown(
    """
    <style>
      .stPlotlyChart {
        border: 1px solid #ddd !important;
        border-radius: 10px !important;
        padding: 0.5rem !important;
        margin-bottom: 1rem !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
# ────────────────────────────────────────────────────────────────────────────

# Sidebar inputs
rig, start_date, end_date, category_windows = render_sidebar()
if end_date < start_date:
    st.sidebar.error("End Date must be on or after Start Date")

# static config for all modules
plotly_template     = get_plotly_template()
grafana_colors      = {"OPEN":"#7EB26D","CLOSE":"#E24D42"}
flow_colors         = {"Low":"#056E5A","Mid":"#292963","High":"#871445"}
flow_category_order = ["Low","Mid","High"]
flow_thresholds = {
    "Annular":(3,7), "Pipe Ram":(5,10),
    "Shear Ram":(6,15),"Casing Shear":(8,18),
    "Connector":(2,5),
}
prefix   = f"pi-no:{rig}.BOP.CBM.Valve_Status"
valve_map = {
    "Upper Blind Shear":prefix+"6",
    "Lower Blind Shear":prefix+"14",
    "LMRP Connector":    prefix+"2",
    "Wellhead Connector":prefix+"11",
    "Upper Pipe Ram":    prefix+"8",
    "Middle Pipe Ram":   prefix+"9",
    "Lower Pipe Ram":    prefix+"10",
    "Upper Annular":     prefix+"1",
    "Lower Annular":     prefix+"5",
    "Test Ram":          prefix+"74",
    "Casing Shear Ram":  prefix+"7",
}
valve_class = {
    "Upper Annular":"Annular","Lower Annular":"Annular",
    "Upper Pipe Ram":"Pipe Ram","Middle Pipe Ram":"Pipe Ram",
    "Lower Pipe Ram":"Pipe Ram","Test Ram":"Pipe Ram",
    "Upper Blind Shear":"Shear Ram","Lower Blind Shear":"Shear Ram",
    "Casing Shear Ram":"Casing Shear",
    "LMRP Connector":"Connector","Wellhead Connector":"Connector",
}
simple_map = {
    256:"CLOSE",257:"OPEN",258:"CLOSE",
    512:"CLOSE",513:"OPEN",514:"CLOSE",
    515:"OPEN",516:"CLOSE",1024:"CLOSE",
    1025:"OPEN",1026:"CLOSE",1027:"OPEN",
    1028:"CLOSE",4096:"ERROR",
}
vol_ext        = f"pi-no:{rig}.BOP.Div_Hpu.HPU_MAINACC_ACC_NONRST"
active_pod_tag = f"pi-no:{rig}.BOP.CBM.ActiveSem_CBM"
pressure_base  = f"pi-no:{rig}.BOP.DCP"
pressure_map   = {
    "Upper Annular":     f"{pressure_base}.ScaledValue12",
    "Lower Annular":     f"{pressure_base}.ScaledValue14",
    "Wellhead Connector":f"{pressure_base}.ScaledValue20",
    "LMRP Connector":    f"{pressure_base}.ScaledValue16",
}
default_pressure = f"{pressure_base}.ScaledValue18"
for v in valve_map:
    pressure_map.setdefault(v, default_pressure)

# ────────── Load Data on button (or first run) ─────────────────────────────
if st.sidebar.button("Load Data") or "df" not in st.session_state:
    with st.spinner("Loading dashboard…"):
        df, vol_df = load_dashboard_data(
            rig,
            start_date,
            end_date,
            category_windows,
            valve_map,
            simple_map,
            valve_class,
            vol_ext,
            pressure_map,
            active_pod_tag,
            flow_thresholds,
        )
        st.session_state.df     = df
        st.session_state.vol_df = vol_df

# ────────── Render Dashboard ────────────────────────────────────────────────
if "df" in st.session_state:
    render_dashboard(
        st.session_state.df,
        st.session_state.vol_df,
        plotly_template,
        grafana_colors,
        flow_colors,
        flow_category_order,
    )
