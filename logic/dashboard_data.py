# logic/dashboard_data.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta

from logic.data_loader    import get_volume_df, get_valve_df, get_pressure_df, get_raw_df
from logic.helpers        import to_ms, classify_flow
from logic.processing     import compute_transitions, extract_ramp
from logic.pressure_utils import assign_max_pressure_vectorized
from logic.depletion      import load_and_preprocess

def _map_active_pod(value: float) -> str:
    if value in (1, 2):
        return "Blue Pod"
    if value in (3, 4):
        return "Yellow Pod"
    return "Unknown"

@st.cache_data(
    ttl=24 * 3600,             # cache for 24 hours
    show_spinner="Loading dashboard…"
)
def load_dashboard_data(
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
):
    # 1) Millisecond bounds
    sm = to_ms(start_date)
    em = to_ms(end_date + timedelta(days=1)) - 1

    # 2) Raw data → transitions → ramp events
    vol_df     = get_volume_df(vol_ext, sm, em)
    valve_list = get_valve_df(valve_map, simple_map, sm, em)
    valve_df   = pd.concat(valve_list).sort_index()
    trans      = compute_transitions(valve_df)
    df         = extract_ramp(trans, vol_df, valve_class, category_windows)

    # 3) Flow Category
    df["Flow Category"] = pd.Categorical(
        df.apply(
            lambda r: classify_flow(
                r["Δ (gal)"],
                valve_class.get(r["valve"], "Pipe Ram"),
                flow_thresholds
            ),
            axis=1
        ),
        categories=["Low", "Mid", "High"],
        ordered=True
    )

    # 4) Max Pressure per event
    df["Max Pressure"] = np.nan
    for p_df in get_pressure_df(pressure_map, sm, em):
        valve_name = p_df["valve"].iat[0]
        p_ser      = p_df.set_index(p_df.index)["pressure"].sort_index()
        mask       = df["valve"] == valve_name
        df.loc[mask, "Max Pressure"] = assign_max_pressure_vectorized(
            df.loc[mask],
            p_ser,
            valve_class,
            category_windows,
        )

    # 5) Active Pod tagging
    pod = (
        get_raw_df(active_pod_tag, sm, em)
        .rename(columns={"value": "ActiveSem_CBM"})
        .astype({"ActiveSem_CBM": "float"})
    )
    pod.index = pd.to_datetime(pod.index)
    pod = pod[["ActiveSem_CBM"]].ffill().bfill()

    df = pd.merge_asof(
        df.sort_values("timestamp"),
        pod,
        left_on="timestamp",
        right_index=True,
        direction="backward"
    )
    df["Active Pod"] = df["ActiveSem_CBM"].apply(_map_active_pod)
    df.drop(columns=["ActiveSem_CBM"], inplace=True)

    # 6) Annotate vol_df for accumulator plot
    vol_annot = vol_df.reset_index().rename(columns={"index": "timestamp"})
    vol_annot = pd.merge_asof(
        vol_annot.sort_values("timestamp"),
        pod,
        left_on="timestamp",
        right_index=True,
        direction="backward"
    )
    vol_annot["Active Pod"] = vol_annot["ActiveSem_CBM"].apply(_map_active_pod)
    vol_annot.set_index("timestamp", inplace=True)
    vol_annot.drop(columns=["ActiveSem_CBM"], inplace=True)

    # 7) Instantaneous flow rate
    dt_s = vol_annot.index.to_series().diff().dt.total_seconds()
    dv   = vol_annot["accumulator"].diff()
    vol_annot["flow_rate_gpm_inst"] = (dv / (dt_s / 60)).bfill()

    # 8) Event-average flow rate
    df["Event Duration (min)"] = (
        (df["End Time"] - df["Start Time"])
        .dt.total_seconds() / 60
    )
    df["Flow Rate (gpm)"] = df["Δ (gal)"] / df["Event Duration (min)"]

    # 9) Merge instantaneous rate onto events
    df = pd.merge_asof(
        df.sort_values("timestamp"),
        vol_annot[["flow_rate_gpm_inst"]]
            .reset_index()
            .rename(columns={"index": "timestamp"}),
        on="timestamp",
        direction="backward"
    )

    # ────────── Enrich with Valve Class, Flow Category, Depletion ──────────
    df = load_and_preprocess(df)

    return df, vol_annot
