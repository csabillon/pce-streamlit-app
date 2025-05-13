import numpy as np
import pandas as pd

def assign_max_pressure_vectorized(events_df, pressure_series, window_sec=30):
    window = pd.Timedelta(seconds=window_sec)
    intervals = pd.IntervalIndex.from_arrays(
        events_df["timestamp"] - window,
        events_df["timestamp"] + window,
        closed="both"
    )
    result = np.full(len(events_df), np.nan)
    for i, interval in enumerate(intervals):
        segment = pressure_series.loc[interval.left:interval.right]
        if not segment.empty:
            result[i] = segment.max()
    return result
