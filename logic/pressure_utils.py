import numpy as np
import pandas as pd

def assign_max_pressure_vectorized(
    events_df: pd.DataFrame,
    pressure_series: pd.Series,
    valve_class: dict[str, str],
    category_windows: dict[str, float],
    pre_frac: float = 0.8,
    post_frac: float = 0.2,
) -> np.ndarray:
    """
    For each event in events_df, look back pre_frac*W seconds and forward post_frac*W seconds 
    (where W = category_windows[valve_class[valve]]), then take the AVERAGE of the top 20%
    of pressure readings in that slice.
    Returns an array of the same length as events_df with that “top‑20% average” for each event.
    """

    # Ensure timestamps are datetime
    ts = pd.to_datetime(events_df["timestamp"])

    # Compute per‑event windows
    pre_offsets = events_df["valve"].map(
        lambda v: pd.Timedelta(seconds=category_windows[valve_class[v]] * pre_frac)
    )
    post_offsets = events_df["valve"].map(
        lambda v: pd.Timedelta(seconds=category_windows[valve_class[v]] * post_frac)
    )

    out = np.full(len(events_df), np.nan)

    for i, (t, pre, post) in enumerate(zip(ts, pre_offsets, post_offsets)):
        window_slice = pressure_series.loc[t - pre : t + post].dropna()

        # Safely convert to numeric numpy array, ignoring errors by coercing to nan then dropping
        arr = pd.to_numeric(window_slice, errors='coerce').dropna().values

        if arr.size == 0:
            continue

        # if fewer than 5 points, just average them all
        if len(arr) < 5:
            out[i] = np.mean(arr)
        else:
            # compute 75th percentile threshold
            thr = np.percentile(arr, 75)
            top_vals = arr[arr >= thr]
            # in edge cases where >=thr yields empty (due to duplicates), fall back to max
            if top_vals.size:
                out[i] = np.mean(top_vals)
            else:
                out[i] = np.max(arr)

    return out
