# logic/dashboard_data.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta

from logic.data_loaders    import get_volume_df, get_valve_df, get_pressure_df, get_raw_df
from logic.preprocessing   import to_ms, classify_flow, compute_transitions, extract_ramp
from logic.pressure        import assign_max_pressure_vectorized, assign_max_well_pressure
from logic.depletion       import load_and_preprocess

def _map_active_pod(value: float) -> str:
    if value in (1, 2):
        return "Blue Pod"
    if value in (3, 4):
        return "Yellow Pod"
    return "Unknown"

def fill_minute_gaps_with_ffill(df, value_col="accumulator"):
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    full_minute_index = pd.date_range(
        start=df.index.min().floor('min'),
        end=df.index.max().ceil('min'),
        freq='1min'
    )
    artificial_df = pd.DataFrame(index=full_minute_index)
    combined = pd.concat([df, artificial_df], axis=0).sort_index()
    combined[value_col] = combined[value_col].ffill()
    return combined

@st.cache_data(
    ttl=24 * 3600,             
    show_spinner="Loading dashboard…"
)
def load_dashboard_data(
    rig,
    start_date,
    end_date,
    category_windows,
    valve_map,
    simple_map,
    function_map,
    valve_class,
    vol_ext,
    pressure_map,
    active_pod_tag,
    flow_thresholds,
):
    sm = to_ms(start_date)
    em = to_ms(end_date + timedelta(days=1)) - 1

    vol_df = get_volume_df(vol_ext, sm, em)
    vol_df = fill_minute_gaps_with_ffill(vol_df, value_col="accumulator")

    valve_list = get_valve_df(valve_map, simple_map, function_map, sm, em)
    valve_df = pd.concat(valve_list).sort_index()

    # Compute transitions (now includes prev_function_state, prev_status_code, etc.)
    trans = compute_transitions(valve_df)

    # No valve_df arg; all needed info is in transitions already
    df = extract_ramp(trans, vol_df, valve_class, category_windows)

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

    # ----------- PRESSURE ASSIGNMENT (with Well Pressure) -------------
    df["Max Pressure"] = np.nan
    well_pressure_series = None

    for p_df in get_pressure_df(pressure_map, sm, em):
        valve_name = p_df["valve"].iat[0]
        p_ser = p_df.set_index(p_df.index)["pressure"].sort_index()
        if valve_name == "Well Pressure":
            well_pressure_series = p_ser
        else:
            mask = df["valve"] == valve_name
            df.loc[mask, "Max Pressure"] = assign_max_pressure_vectorized(
                df.loc[mask],
                p_ser,
                valve_class,
                category_windows,
            )

    if well_pressure_series is not None:
        df["Max Well Pressure"] = assign_max_well_pressure(
            df, well_pressure_series, valve_class, category_windows
        )
    else:
        df["Max Well Pressure"] = np.nan

    # ---- Pod tagging, flow rate, etc (unchanged) ----
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

    dt_s = vol_annot.index.to_series().diff().dt.total_seconds()
    dv = vol_annot["accumulator"].diff()
    vol_annot["flow_rate_gpm_inst"] = (dv / (dt_s / 60)).bfill()

    df["Duration (min)"] = (
        (df["End Time"] - df["Start Time"])
        .dt.total_seconds() / 60
    )
    df["Flow Rate (gpm)"] = df["Δ (gal)"] / df["Duration (min)"]

    df = pd.merge_asof(
        df.sort_values("timestamp"),
        vol_annot[["flow_rate_gpm_inst"]]
            .reset_index()
            .rename(columns={"index": "timestamp"}),
        on="timestamp",
        direction="backward"
    )

    df = load_and_preprocess(df)

    return df, vol_annot

def get_timeseries_data(tag, start_date, end_date):
    sm = to_ms(start_date)
    em = to_ms(end_date + timedelta(days=1)) - 1

    df = get_raw_df(tag, sm, em)
    if not df.empty:
        if 'timestamp' not in df.columns:
            df = df.reset_index().rename(columns={df.index.name or 'index': 'timestamp'})
        if 'value' not in df.columns:
            value_cols = [col for col in df.columns if col not in ('timestamp', 'index')]
            if value_cols:
                df = df.rename(columns={value_cols[0]: 'value'})
        return df[['timestamp', 'value']]
    else:
        return pd.DataFrame(columns=['timestamp', 'value'])
