# app.py

import streamlit as st
from utils.themes         import get_plotly_template
from ui.layout            import render_sidebar
from logic.dashboard_data import load_dashboard_data
from logic.depletion      import VALVE_CLASS_MAP, FLOW_THRESHOLDS
from ui.dashboard         import render_dashboard
from ui.overview          import render_overview
from utils.colors         import OC_COLORS, BY_COLORS, FLOW_COLORS, FLOW_CATEGORY_ORDER

# ────────── Page config & CSS ─────────────────────────────────────────────
st.set_page_config(page_title="BOP Valve Dashboard", layout="wide")
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
    </style>
""", unsafe_allow_html=True)

# ────────── Deep-link support via URL params ───────────────────────────────
params          = st.query_params
requested_rig   = params.get("rig", [])   # e.g. "TODPS"
requested_page  = params.get("page", [])  # e.g. "Pods Overview"


#st.write("🕵️‍♂️ requested_rig  =", requested_rig)
#st.write("🕵️‍♂️ requested_pg   =", requested_page)


# Map your Angular rig IDs to the sidebar labels
rig_map = {
    "TODPS": "TransoceanDPS",
    "TODTH": "TransoceanDTH",
    "TODPT": "TransoceanDPT",
}
default_rig = rig_map.get(requested_rig, None)

# ────────── Sidebar inputs & rig selector ────────────────────────────────
rig, start_date, end_date, category_windows = render_sidebar(default_rig)
if end_date < start_date:
    st.sidebar.error("End Date must be on or after Start Date")

# ────────── Page selector with deep-link ─────────────────────────────────
all_pages = ["Valve Analytics", "Pods Overview"]
if requested_page in all_pages:
    page_index = all_pages.index(requested_page)
else:
    page_index = 0

page = st.sidebar.radio(
    "Select Page",
    all_pages,
    index=page_index,
)



# ────────── Static config ─────────────────────────────────────────────────
plotly_template     = get_plotly_template()
oc_colors           = OC_COLORS
by_colors           = BY_COLORS
flow_colors         = FLOW_COLORS
flow_category_order = FLOW_CATEGORY_ORDER

# ────────── Valve tag mappings ────────────────────────────────────────────
_prefix = f"pi-no:{rig}.BOP.CBM.Valve_Status"
valve_map = {
    "Upper Annular":      _prefix + "1",
    "Lower Annular":      _prefix + "5",
    "LMRP Connector":     _prefix + "2",
    "Upper Blind Shear":  _prefix + "6",
    "Casing Shear Ram":   _prefix + "7",
    "Lower Blind Shear":  _prefix + "14",
    "Upper Pipe Ram":     _prefix + "8",
    "Middle Pipe Ram":    _prefix + "9",
    "Lower Pipe Ram":     _prefix + "10",
    "Test Ram":           _prefix + "74",
    "Wellhead Connector": _prefix + "11",
}
valve_order = list(valve_map.keys())

vol_ext        = f"pi-no:{rig}.BOP.Div_Hpu.HPU_MAINACC_ACC_NONRST"
active_pod_tag = f"pi-no:{rig}.BOP.CBM.ActiveSem_CBM"

pressure_base = f"pi-no:{rig}.BOP.DCP"
pressure_map  = {
    **{v: f"{pressure_base}.ScaledValue{n}" for v,n in [
        ("Upper Annular", 12),
        ("Lower Annular", 14),
        ("Wellhead Connector", 20),
        ("LMRP Connector", 16),
    ]},
}
default_press_tag = f"{pressure_base}.ScaledValue18"
for v in valve_map:
    pressure_map.setdefault(v, default_press_tag)

simple_map = {
    256: "CLOSE", 257: "OPEN", 258: "CLOSE",
    512: "CLOSE", 513: "OPEN", 514: "CLOSE",
    515: "OPEN", 516: "CLOSE", 1024: "CLOSE",
    1025: "OPEN", 1026: "CLOSE", 1027: "OPEN",
    1028: "CLOSE", 4096: "ERROR",
}

# ────────── Load Data on button (or first run) ────────────────────────────
if st.sidebar.button("Load Data") or "df" not in st.session_state:
    with st.spinner("Loading dashboard…"):
        df, vol_df = load_dashboard_data(
            rig,
            start_date,
            end_date,
            category_windows,
            valve_map,
            simple_map,
            VALVE_CLASS_MAP,
            vol_ext,
            pressure_map,
            active_pod_tag,
            FLOW_THRESHOLDS,
        )
        st.session_state.df     = df
        st.session_state.vol_df = vol_df

# ────────── Render Selected Page ───────────────────────────────────────────
if "df" in st.session_state:
    if page == "Valve Analytics":
        render_dashboard(
            st.session_state.df,
            st.session_state.vol_df,
            plotly_template,
            oc_colors,
            flow_colors,
            flow_category_order,
            valve_order,
        )
    else:
        render_overview(
            st.session_state.df,
            st.session_state.vol_df,
            plotly_template,
            oc_colors,
            by_colors,
            flow_colors,
            flow_category_order,
        )
else:
    st.info("Please click **Load Data** in the sidebar to get started.")
