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
import pandas as pd

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

available_pages = ["Valve Analytics", "Pods Overview", "EDS Cycles", "Pressure Cycles"]
requested_page = params.get("page")
page_from_deeplink = requested_page if requested_page in available_pages else available_pages[0]

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

sidebar_args = dict(default_rig=default_rig, default_page=page_from_deeplink)
rig, start_date, end_date, category_windows, page = render_sidebar(**sidebar_args)

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

# Load analytics data (+ precomputed cycles + well pressure)
if data_key not in st.session_state:
    df, vol_df, cycles_df, well_pressure_series = load_dashboard_data(
        rig, start_date, end_date, category_windows, valve_map,
        per_valve_simple_map, per_valve_function_map,
        VALVE_CLASS_MAP, vol_ext, pressure_map,
        active_pod_tag, FLOW_THRESHOLDS
    )
    st.session_state[data_key] = (df, vol_df, cycles_df, well_pressure_series)
else:
    df, vol_df, cycles_df, well_pressure_series = st.session_state[data_key]

# Apply Rare threshold globally to cycles (default 2500 psi)
rare_thr = int(st.session_state.get("rare_cycle_threshold", 2500))
filtered_cycles_df = cycles_df
if isinstance(cycles_df, pd.DataFrame) and not cycles_df.empty:
    filtered_cycles_df = cycles_df[cycles_df["Max Well Pressure"] >= rare_thr].copy()

# Pressure series cache (for regulator traces)
pressure_key = data_key + "_pressure"
if pressure_key not in st.session_state:
    sm = to_ms(start_date)
    em = to_ms(end_date + timedelta(days=1)) - 1
    pressure_results = get_pressure_df(pressure_map, sm, em)

    pressure_series_by_valve = {}
    wp_series = well_pressure_series

    for p_df in pressure_results:
        valve_name = p_df["valve"].iat[0]
        p_ser = p_df.set_index(p_df.index)["pressure"].sort_index()
        p_ser.index = pd.to_datetime(p_ser.index)
        pressure_series_by_valve[valve_name] = p_ser

    regulator_pressure_series_map = {}
    for v in valve_order:
        ser = pressure_series_by_valve.get(v)
        regulator_pressure_series_map[v] = ser

    st.session_state[pressure_key] = {
        "pressure_series_by_valve": pressure_series_by_valve,
        "well_pressure_series": wp_series,
        "regulator_pressure_series_map": regulator_pressure_series_map,
    }
else:
    _prs = st.session_state[pressure_key]
    pressure_series_by_valve = _prs["pressure_series_by_valve"]
    if well_pressure_series is None:
        well_pressure_series = _prs["well_pressure_series"]
    regulator_pressure_series_map = _prs["regulator_pressure_series_map"]

# Sync URL with page
if st.query_params.get("page") != page:
    st.query_params["page"] = page

# Render
if df is not None and vol_df is not None:
    if page == "Valve Analytics":
        render_dashboard(
            df=df,
            vol_df=vol_df,
            plotly_template=plotly_template,
            oc_colors=oc_colors,
            flow_colors=flow_colors,
            flow_category_order=flow_category_order,
            valve_order=valve_order,
            cycles_df=filtered_cycles_df,  # cycles already filtered by Rare
        )

    elif page == "Pods Overview":
        render_overview(
            df=df,
            vol_df=vol_df,
            plotly_template=plotly_template,
            oc_colors=oc_colors,
            by_colors=by_colors,
            flow_colors=flow_colors,
            flow_category_order=flow_category_order,
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
        if isinstance(well_pressure_series, pd.Series) and not well_pressure_series.empty:
            render_pressure_cycles(
                df=df,
                valve_map=valve_map,
                well_pressure_series=well_pressure_series,
                pressure_series_by_valve=regulator_pressure_series_map,
                cycles_df=filtered_cycles_df,  # cycles already filtered by Rare
            )
        else:
            st.warning("No well pressure data available for analysis.")
else:
    st.info("Please click **Load Data** in the sidebar to get started.")
