# logic/preprocessing.py

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("preprocessing")

def compute_transitions(valve_df):
    if valve_df.empty:
        logger.warning("[PREPROCESS] compute_transitions: Empty valve_df")
        return pd.DataFrame()
    valve_df = valve_df.reset_index().rename(columns={"index": "timestamp"})
    valve_df["prev_state"] = valve_df.groupby("valve")["state"].shift(1)
    valve_df["prev_function_state"] = valve_df.groupby("valve")["function_state"].shift(1)
    valve_df["prev_status_code"] = valve_df.groupby("valve")["status_code"].shift(1)
    # Only actual state changes, drop rows with no transition or missing state
    result = valve_df[valve_df["state"] != valve_df["prev_state"]].dropna()
    if result.empty:
        logger.warning("[PREPROCESS] No state transitions detected.")
    return result

def extract_ramp(transitions, vol_df, valve_class, category_windows):
    rows = []
    if transitions.empty or vol_df.empty:
        logger.warning("[PREPROCESS] extract_ramp: Empty transitions or volume data")
        return pd.DataFrame()
    vol = vol_df.copy()
    vol.index = pd.to_datetime(vol.index)
    trans = transitions.copy()
    trans["timestamp"] = pd.to_datetime(trans["timestamp"])
    used = []
    skipped = 0
    for _, row in trans.iterrows():
        valve = row["valve"]
        t = row["timestamp"]
        vclass = valve_class.get(valve, "Pipe Ram")
        W = pd.Timedelta(seconds=category_windows.get(vclass, 60))
        t0 = t - 0.8 * W
        t1 = t + 0.2 * W
        if any((t0 <= end and t1 >= start) for start, end in used):
            skipped += 1
            continue
        segment = vol[(vol.index >= t0) & (vol.index <= t1)].copy()
        if segment.empty:
            continue
        segment["delta"] = segment["accumulator"].diff()
        ramp = segment
        if ramp.empty:
            continue
        start_ts = ramp.index[0]
        end_ts   = ramp.index[-1]
        start_val = segment.loc[:start_ts]["accumulator"].iloc[-1]
        end_val   = segment.loc[end_ts:]["accumulator"].iloc[0]
        delta     = end_val - start_val
        prev_function_state = row.get("prev_function_state", None)
        function_state = row.get("function_state", None)
        status_code = row.get("status_code", None)
        rows.append({
            "timestamp":    t,
            "valve":        valve,
            "prev_state":   row["prev_state"],
            "state":        row["state"],
            "function_state": function_state,
            "status_code": status_code,
            "Start Time":   start_ts,
            "End Time":     end_ts,
            "Start (gal)":  start_val,
            "End (gal)":    end_val,
            "Δ (gal)":      delta,
        })
        used.append((t0, t1))
    if skipped > 0:
        logger.info(f"[PREPROCESS] {skipped} events skipped due to overlap window.")
    if not rows:
        logger.warning("[PREPROCESS] extract_ramp: No events extracted.")
    return pd.DataFrame(rows)

def to_ms(dt):
    return int(pd.Timestamp(dt).timestamp() * 1000)

def classify_flow(delta_gal, valve_class, flow_thresholds):
    low, high = flow_thresholds.get(valve_class, (float("inf"), float("inf")))
    if delta_gal <= low:
        return "Low"
    elif delta_gal <= high:
        return "Mid"
    else:
        return "High"

def downsample_for_display(df, target_points=4000, method="nth"):
    if df.empty:
        return df
    if len(df) <= target_points:
        return df
    if method == "nth":
        step = max(1, len(df) // target_points)
        return df.iloc[::step]
    elif method == "resample" and isinstance(df.index, pd.DatetimeIndex):
        return df.resample('1T').mean()
    else:
        return df
