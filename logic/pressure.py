# logic/pressure.py

import numpy as np
import pandas as pd

def assign_max_pressure_vectorized(
    events_df: pd.DataFrame,
    pressure_series: pd.Series,
    valve_class: dict,
    category_windows: dict,
    pre_frac: float = 0.8,
    post_frac: float = 0.2,
) -> np.ndarray:
    """
    For each event in events_df, look back pre_frac*W seconds and forward post_frac*W seconds 
    (where W = category_windows[valve_class[valve]]), then take the AVERAGE of the top 20%
    of pressure readings in that slice.
    Returns an array of the same length as events_df with that “top‑20% average” for each event.
    """
    ts = pd.to_datetime(events_df["timestamp"])
    pre_offsets = events_df["valve"].map(
        lambda v: pd.Timedelta(seconds=category_windows[valve_class[v]] * pre_frac)
    )
    post_offsets = events_df["valve"].map(
        lambda v: pd.Timedelta(seconds=category_windows[valve_class[v]] * post_frac)
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
    """
    For each event, calculates the max well pressure within a window:
      - "OPEN": [t - 0.8W, t + 2W]
      - "CLOSE": [t - 0.8W, next OPEN event for same valve] (or end of well_pressure_series)
    Returns an array of same length as events_df.
    """
    ts = pd.to_datetime(events_df["timestamp"])
    states = events_df["state"].values
    valves = events_df["valve"].values
    n = len(events_df)
    out = np.full(n, np.nan)

    for i in range(n):
        state = states[i]
        t = ts[i]
        valve = valves[i]
        w = pd.Timedelta(seconds=category_windows[valve_class[valve]])
        pre = 0.8 * w

        if state == "OPEN":
            post = 2.0 * w
            start = t - pre
            end = t + post
        else:  # "CLOSE"
            start = t - pre
            # Find the next "OPEN" event for this valve
            mask = (valves == valve) & (ts > t) & (states == "OPEN")
            if mask.any():
                next_open_time = ts[mask].min()
                end = next_open_time
            else:
                end = well_pressure_series.index.max()  # till end of data

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
