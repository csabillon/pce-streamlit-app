# app.py

from cognite.client.config import global_config

import streamlit as st
from utils.themes import get_plotly_template
from ui.sidebar import render_sidebar
from logic.dashboard_data import load_dashboard_data
from logic.depletion import VALVE_CLASS_MAP, FLOW_THRESHOLDS
from ui.dashboard import render_dashboard
from ui.overview import render_overview
from ui.eds_cycles import render_eds_cycles
from ui.pressure_cycles import render_pressure_cycles
from utils.colors import OC_COLORS, BY_COLORS, FLOW_COLORS, FLOW_CATEGORY_ORDER
from logic.tag_maps import get_rig_tags
from logic.data_loaders import get_pressure_df
from logic.preprocessing import to_ms
from datetime import timedelta

st.set_page_config(
    page_title="BOP Valve Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .stPlotlyChart {
    border: 1px solid #ddd !important;
    border-radius: 10px !important;
    padding: 0.5rem !important;
    margin-bottom: 1rem !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
  }
  .stDeployButton,
  .stAppDeployButton,
  button[data-testid="stAppViewDeployButton"] {
    display: none !important;
  }
</style>
""", unsafe_allow_html=True)

params = st.query_params
requested_rig = params.get("rig")
requested_theme = params.get("theme")

if requested_theme in ("dark", "light"):
    st._config.set_option("theme.base", requested_theme)

plotly_template = get_plotly_template()

rig_map = {
    "TODPS": "TransoceanDPS",
    "TODTH": "TransoceanDTH",
    "TODPT": "TransoceanDPT",
    "STDMX": "Drillmax",
}
default_rig = rig_map.get(requested_rig, None)

# Updated: get page from sidebar!
rig, start_date, end_date, category_windows, page = render_sidebar(default_rig)

oc_colors = OC_COLORS
by_colors = BY_COLORS
flow_colors = FLOW_COLORS
flow_category_order = FLOW_CATEGORY_ORDER

tags = get_rig_tags(rig)
valve_map = tags["valve_map"]
vol_ext = tags["vol_ext"]
active_pod_tag = tags["active_pod_tag"]
pressure_map = tags["pressure_map"]
eds_base_tag = tags["eds_base_tag"]

valve_order = list(valve_map.keys())

# Update here: Use your new simple/function maps
simple_map = {
    256: "VENT",
    513: "OPEN", 514: "CLOSE", 515: "OPEN VENT", 516: "CLOSE VENT",
    1025: "OPEN", 1026: "CLOSE", 1027: "OPEN VENT", 1028: "CLOSE VENT",
    4096: "ERROR",
}
function_map = {
    256: "VENT",
    513: "OPEN", 514: "CLOSE", 515: "OPEN VENT", 516: "CLOSE VENT",
    1025: "OPEN", 1026: "CLOSE", 1027: "OPEN VENT", 1028: "CLOSE VENT",
    4096: "ERROR",
}

# Smarter caching: reloads if ANY of these parameters change (including embedded links)
data_key = f"{rig}_{start_date}_{end_date}"
if st.sidebar.button("Reload Data"):
    if data_key in st.session_state:
        del st.session_state[data_key]

if data_key not in st.session_state:
    df, vol_df = load_dashboard_data(
        rig, start_date, end_date, category_windows, valve_map,
        simple_map, function_map, VALVE_CLASS_MAP, vol_ext, pressure_map,
        active_pod_tag, FLOW_THRESHOLDS
    )
    st.session_state[data_key] = (df, vol_df)
else:
    df, vol_df = st.session_state[data_key]

if df is not None and vol_df is not None:
    if page == "Valve Analytics":
        render_dashboard(
            df, vol_df, plotly_template,
            oc_colors, flow_colors, flow_category_order, valve_order,
        )
    elif page == "Pods Overview":
        render_overview(
            df, vol_df, plotly_template,
            oc_colors, by_colors, flow_colors, flow_category_order,
        )
    elif page == "EDS Cycles":
        render_eds_cycles(
            rig, start_date, end_date,
            valve_map=valve_map,
            simple_map=simple_map,
            vol_ext=vol_ext,
            active_pod_tag=active_pod_tag,
            eds_base_tag=eds_base_tag,
        )
    elif page == "Pressure Cycles":
        # ----------- Well Pressure Extraction -----------
        sm = to_ms(start_date)
        em = to_ms(end_date + timedelta(days=1)) - 1
        well_pressure_series = None
        for p_df in get_pressure_df(pressure_map, sm, em):
            valve_name = p_df["valve"].iat[0]
            if valve_name == "Well Pressure":
                well_pressure_series = p_df.set_index(p_df.index)["pressure"].sort_index()
                break
        # -----------------------------------------------
        if well_pressure_series is not None:
            render_pressure_cycles(
                df, valve_map, well_pressure_series
            )
        else:
            st.warning("No well pressure data available for analysis.")
else:
    st.info("Please click **Load Data** in the sidebar to get started.")
