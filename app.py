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
per_valve_simple_map = tags["per_valve_simple_map"]
per_valve_function_map = tags["per_valve_function_map"]
valve_order = list(valve_map.keys())

data_key = f"{rig}_{start_date}_{end_date}"
if st.sidebar.button("Reload Data"):
    for key in [data_key, data_key + "_pressure"]:
        if key in st.session_state:
            del st.session_state[key]

# Load valve/volume analytics data
if data_key not in st.session_state:
    df, vol_df = load_dashboard_data(
        rig, start_date, end_date, category_windows, valve_map,
        per_valve_simple_map, per_valve_function_map,
        VALVE_CLASS_MAP, vol_ext, pressure_map,
        active_pod_tag, FLOW_THRESHOLDS
    )
    st.session_state[data_key] = (df, vol_df)
else:
    df, vol_df = st.session_state[data_key]

# --- PRESSURE SERIES LOADING AND CACHING (all at once!) ---
pressure_key = data_key + "_pressure"
if pressure_key not in st.session_state:
    sm = to_ms(start_date)
    em = to_ms(end_date + timedelta(days=1)) - 1
    pressure_results = get_pressure_df(pressure_map, sm, em)
    pressure_series_by_valve = {}
    well_pressure_series = None
    # Assign all as Series for easy access
    for p_df in pressure_results:
        valve_name = p_df["valve"].iat[0]
        p_ser = p_df.set_index(p_df.index)["pressure"].sort_index()
        pressure_series_by_valve[valve_name] = p_ser
        # Pick well pressure
        if valve_name.lower().startswith("well pressure"):
            well_pressure_series = p_ser
    # Regulator pressure: try by name for each valve, fallback to default if needed
    regulator_pressure_series_map = {}
    for v in valve_order:
        # Try to match by valve name (exact, case-insensitive, or "Regulator Pressure")
        found = None
        for key in pressure_series_by_valve:
            if key.lower().startswith("regulator pressure") or key.lower().startswith("regulator"):
                found = key
                break
            if key.lower() == v.lower():
                found = key
        if found:
            regulator_pressure_series_map[v] = pressure_series_by_valve[found]
        else:
            regulator_pressure_series_map[v] = None
    st.session_state[pressure_key] = {
        "pressure_series_by_valve": pressure_series_by_valve,
        "well_pressure_series": well_pressure_series,
        "regulator_pressure_series_map": regulator_pressure_series_map,
    }
else:
    _prs = st.session_state[pressure_key]
    pressure_series_by_valve = _prs["pressure_series_by_valve"]
    well_pressure_series = _prs["well_pressure_series"]
    regulator_pressure_series_map = _prs["regulator_pressure_series_map"]

# --- MAIN PAGE HANDLING ---
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
            per_valve_simple_map=per_valve_simple_map,
            per_valve_function_map=per_valve_function_map,
            vol_ext=vol_ext,
            active_pod_tag=active_pod_tag,
            eds_base_tag=eds_base_tag,
        )
    elif page == "Pressure Cycles":
        if well_pressure_series is not None:
            render_pressure_cycles(
                df=df,
                valve_map=valve_map,
                well_pressure_series=well_pressure_series,
                pressure_series_by_valve=regulator_pressure_series_map,
            )
        else:
            st.warning("No well pressure data available for analysis.")
else:
    st.info("Please click **Load Data** in the sidebar to get started.")
