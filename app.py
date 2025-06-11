import streamlit as st
from utils.themes import get_plotly_template
from ui.layout import render_sidebar
from logic.dashboard_data import load_dashboard_data
from logic.depletion import VALVE_CLASS_MAP, FLOW_THRESHOLDS
from ui.page_dashboard import render_dashboard
from ui.page_overview import render_overview
from ui.page_eds_cycles import render_eds_cycles
from utils.colors import OC_COLORS, BY_COLORS, FLOW_COLORS, FLOW_CATEGORY_ORDER
from utils.tag_mappings import get_rig_tags

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

# URL Params
params = st.query_params
requested_rig = params.get("rig", None)
requested_page = params.get("page", None)
requested_theme = params.get("theme", None)

requested_rig = requested_rig if requested_rig else None
requested_page = requested_page if requested_page else None
requested_theme = requested_theme if requested_theme else None

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

# Sidebar
rig, start_date, end_date, category_windows = render_sidebar(default_rig)

# Page selection
all_pages = ["Valve Analytics", "Pods Overview", "EDS Cycles"]
page_index = all_pages.index(requested_page) if requested_page in all_pages else 0
page = st.sidebar.radio("Select Page", all_pages, index=page_index)

# Colors
oc_colors = OC_COLORS
by_colors = BY_COLORS
flow_colors = FLOW_COLORS
flow_category_order = FLOW_CATEGORY_ORDER

# Get rig-specific tags from modular function
tags = get_rig_tags(rig)
valve_map = tags["valve_map"]
vol_ext = tags["vol_ext"]
active_pod_tag = tags["active_pod_tag"]
pressure_map = tags["pressure_map"]
eds_base_tag = tags["eds_base_tag"]

valve_order = list(valve_map.keys())

simple_map = {
    256: "CLOSE", 257: "OPEN", 258: "CLOSE",
    512: "CLOSE", 513: "OPEN", 514: "CLOSE",
    515: "OPEN", 516: "CLOSE", 1024: "CLOSE",
    1025: "OPEN", 1026: "CLOSE", 1027: "OPEN",
    1028: "CLOSE", 4096: "ERROR",
}

# Data loading without spinner
if st.sidebar.button("Load Data") or "df" not in st.session_state:
    df, vol_df = load_dashboard_data(
        rig, start_date, end_date, category_windows, valve_map,
        simple_map, VALVE_CLASS_MAP, vol_ext, pressure_map,
        active_pod_tag, FLOW_THRESHOLDS
    )
    st.session_state.df = df
    st.session_state.vol_df = vol_df

# Render
if "df" in st.session_state:
    if page == "Valve Analytics":
        render_dashboard(
            st.session_state.df, st.session_state.vol_df, plotly_template,
            oc_colors, flow_colors, flow_category_order, valve_order,
        )
    elif page == "Pods Overview":
        render_overview(
            st.session_state.df, st.session_state.vol_df, plotly_template,
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
else:
    st.info("Please click **Load Data** in the sidebar to get started.")
