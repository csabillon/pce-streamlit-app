# logic/pressure_utils.py

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
    (where W = category_windows[valve_class[valve]]), then take the max pressure in that slice.
    Returns an array of the same length as events_df with the max‐pressure for each event.
    """
    # Ensure timestamps are datetime
    ts = pd.to_datetime(events_df["timestamp"])
    # Build per‐event pre/post offsets
    # e.g. for valve "Annular" with slider=30 → W=30s → pre=24s, post=6s
    pre_offsets = events_df["valve"].map(lambda v: pd.Timedelta(seconds=category_windows[valve_class[v]] * pre_frac))
    post_offsets = events_df["valve"].map(lambda v: pd.Timedelta(seconds=category_windows[valve_class[v]] * post_frac))

    out = np.full(len(events_df), np.nan)
    for i, (t, pre, post) in enumerate(zip(ts, pre_offsets, post_offsets)):
        window_slice = pressure_series.loc[t - pre : t + post]
        if not window_slice.empty:
            out[i] = window_slice.max()
    return out
