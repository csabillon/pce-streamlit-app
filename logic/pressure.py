# logic/pressure.py

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("pressure")

def assign_max_pressure_vectorized(
    events_df: pd.DataFrame,
    pressure_series: pd.Series,
    valve_class: dict,
    category_windows: dict,
    pre_frac: float = 0.8,
    post_frac: float = 0.2,
) -> np.ndarray:
    if events_df.empty or pressure_series.empty:
        logger.warning("[PRESSURE] assign_max_pressure_vectorized: Empty input.")
        return np.full(len(events_df), np.nan)
    ts = pd.to_datetime(events_df["timestamp"])
    pre_offsets = events_df["valve"].map(
        lambda v: pd.Timedelta(seconds=category_windows.get(valve_class.get(v, "Pipe Ram"), 60) * pre_frac)
    )
    post_offsets = events_df["valve"].map(
        lambda v: pd.Timedelta(seconds=category_windows.get(valve_class.get(v, "Pipe Ram"), 60) * post_frac)
    )
    out = np.full(len(events_df), np.nan)
    for i, (t, pre, post) in enumerate(zip(ts, pre_offsets, post_offsets)):
        window_slice = pressure_series.loc[t - pre : t + post].dropna()
        arr = pd.to_numeric(window_slice, errors='coerce').dropna().values
        if arr.size == 0:
            continue
        if len(arr) < 5:
            out[i] = np.mean(arr)
        else:
            thr = np.percentile(arr, 75)
            top_vals = arr[arr >= thr]
            out[i] = np.mean(top_vals) if top_vals.size else np.max(arr)
    return out

def assign_max_well_pressure(
    events_df: pd.DataFrame,
    well_pressure_series: pd.Series,
    valve_class: dict,
    category_windows: dict,
) -> np.ndarray:
    if events_df.empty or well_pressure_series.empty:
        logger.warning("[PRESSURE] assign_max_well_pressure: Empty input.")
        return np.full(len(events_df), np.nan)
    ts = pd.to_datetime(events_df["timestamp"])
    states = events_df["state"].values
    valves = events_df["valve"].values
    n = len(events_df)
    out = np.full(n, np.nan)
    for i in range(n):
        state = states[i]
        t = ts[i]
        valve = valves[i]
        vclass = valve_class.get(valve, "Pipe Ram")
        w = pd.Timedelta(seconds=category_windows.get(vclass, 60))
        pre = 0.8 * w
        if state == "OPEN":
            post = 2.0 * w
            start = t - pre
            end = t + post
        else:  # "CLOSE"
            start = t - pre
            mask = (valves == valve) & (ts > t) & (states == "OPEN")
            if mask.any():
                next_open_time = ts[mask].min()
                end = next_open_time
            else:
                end = well_pressure_series.index.max()
        window_slice = well_pressure_series.loc[start:end].dropna()
        arr = pd.to_numeric(window_slice, errors='coerce').dropna().values
        if arr.size == 0:
            continue
        if len(arr) < 5:
            out[i] = np.mean(arr)
        else:
            thr = np.percentile(arr, 75)
            top_vals = arr[arr >= thr]
            out[i] = np.mean(top_vals) if top_vals.size else np.max(arr)
    return out
