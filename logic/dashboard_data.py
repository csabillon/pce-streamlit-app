# logic/dashboard_data.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
from functools import lru_cache
import logging

from logic.data_loaders    import get_volume_df, get_valve_df, get_pressure_df, get_raw_df
from logic.preprocessing   import to_ms, classify_flow, compute_transitions, extract_ramp
from logic.pressure        import assign_max_pressure_vectorized, assign_max_well_pressure
from logic.depletion       import load_and_preprocess, FLOW_THRESHOLDS, VALVE_CLASS_MAP

logger = logging.getLogger("dashboard_data")

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

@lru_cache(maxsize=8)
def get_flow_thresholds_tuple(valve_class: str):
    return FLOW_THRESHOLDS.get(valve_class, (float("inf"), float("inf")))

@st.cache_data(ttl=24 * 3600, show_spinner="Loading dashboard…")
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
    if vol_df.empty:
        logger.warning("[DASHBOARD] vol_df is empty")
        vol_df["accumulator"] = np.nan
    vol_df = fill_minute_gaps_with_ffill(vol_df, value_col="accumulator")

    valve_list = get_valve_df(valve_map, simple_map, function_map, sm, em)
    valve_list = [v for v in valve_list if not v.empty]
    if not valve_list:
        logger.warning("[DASHBOARD] No valve data loaded")
        return pd.DataFrame(), pd.DataFrame()
    valve_df = pd.concat(valve_list).sort_index()

    try:
        trans = compute_transitions(valve_df)
    except Exception as e:
        logger.error(f"[DASHBOARD] Failed to compute transitions: {e}")
        return pd.DataFrame(), pd.DataFrame()

    try:
        df = extract_ramp(trans, vol_df, valve_class, category_windows)
    except Exception as e:
        logger.error(f"[DASHBOARD] Failed to extract ramp: {e}")
        return pd.DataFrame(), pd.DataFrame()

    if df.empty:
        logger.warning("[DASHBOARD] No transitions extracted")
        return pd.DataFrame(), pd.DataFrame()

    # Vectorized flow category assignment
    valve_class_col = df["valve"].map(valve_class)
    low = valve_class_col.map(lambda v: flow_thresholds.get(v, (float("inf"), float("inf")))[0])
    high = valve_class_col.map(lambda v: flow_thresholds.get(v, (float("inf"), float("inf")))[1])
    df["Flow Category"] = np.select(
        [df["Δ (gal)"] <= low, df["Δ (gal)"] <= high],
        ["Low", "Mid"],
        default="High"
    )
    df["Flow Category"] = pd.Categorical(df["Flow Category"], categories=["Low", "Mid", "High"], ordered=True)

    df["Max Pressure"] = np.nan
    well_pressure_series = None

    for p_df in get_pressure_df(pressure_map, sm, em):
        if p_df.empty:
            continue
        valve_name = p_df["valve"].iat[0]
        p_ser = p_df.set_index(p_df.index)["pressure"].sort_index()
        if valve_name == "Well Pressure":
            well_pressure_series = p_ser
        else:
            mask = df["valve"] == valve_name
            if mask.any():
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

    # Pod tagging
    pod = get_raw_df(active_pod_tag, sm, em)
    if not pod.empty:
        pod = pod.rename(columns={"value": "ActiveSem_CBM"}).astype({"ActiveSem_CBM": "float"})
        pod.index = pd.to_datetime(pod.index)
        pod = pod[["ActiveSem_CBM"]].ffill().bfill()
    else:
        logger.warning("[DASHBOARD] Pod signal empty")
        pod = pd.DataFrame(columns=["ActiveSem_CBM"])

    df = pd.merge_asof(
        df.sort_values("timestamp"),
        pod,
        left_on="timestamp",
        right_index=True,
        direction="backward"
    )
    df["Active Pod"] = df["ActiveSem_CBM"].apply(_map_active_pod)
    df.drop(columns=["ActiveSem_CBM"], inplace=True, errors="ignore")

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
    vol_annot.drop(columns=["ActiveSem_CBM"], inplace=True, errors="ignore")

    dt_s = vol_annot.index.to_series().diff().dt.total_seconds()
    dv = vol_annot["accumulator"].diff()
    vol_annot["flow_rate_gpm_inst"] = (dv / (dt_s / 60)).bfill()

    df["Duration (min)"] = (df["End Time"] - df["Start Time"]).dt.total_seconds() / 60
    with np.errstate(divide="ignore", invalid="ignore"):
        df["Flow Rate (gpm)"] = np.where(df["Duration (min)"] > 0, df["Δ (gal)"] / df["Duration (min)"], np.nan)

    df = pd.merge_asof(
        df.sort_values("timestamp"),
        vol_annot[["flow_rate_gpm_inst"]].reset_index().rename(columns={"index": "timestamp"}),
        on="timestamp",
        direction="backward"
    )

    try:
        df = load_and_preprocess(df)
    except Exception as e:
        logger.error(f"[DASHBOARD] load_and_preprocess failed: {e}")

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
        logger.warning(f"[DASHBOARD] get_timeseries_data: No data for {tag}")
        return pd.DataFrame(columns=['timestamp', 'value'])
