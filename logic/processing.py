import pandas as pd

def compute_transitions(valve_df):
    valve_df = valve_df.reset_index().rename(columns={"index": "timestamp"})
    valve_df["prev_state"] = valve_df.groupby("valve")["state"].shift(1)
    return valve_df[valve_df["state"] != valve_df["prev_state"]].dropna()

def extract_ramp(transitions, vol_df, valve_class, category_windows):
    """
    For each valve transition, look in a total window W around the event (80% before, 20% after),
    find the “ramp” portion (delta > 80th percentile), and record:
      - timestamp (event time)
      - valve, prev_state, state
      - Start Time / End Time (exact timestamps of accumulator start/end)
      - Start (gal), End (gal), Δ (gal)
    Skips any event whose [t0, t1] overlaps one already used.
    """
    rows = []
    vol = vol_df.copy()
    vol.index = pd.to_datetime(vol.index)
    trans = transitions.copy()
    trans["timestamp"] = pd.to_datetime(trans["timestamp"])

    used = []
    for _, row in trans.iterrows():
        valve = row["valve"]
        t = row["timestamp"]
        W = pd.Timedelta(seconds=category_windows[valve_class[valve]])
        # 80% before, 20% after → total span = W
        t0 = t - 0.8 * W
        t1 = t + 0.2 * W

        # skip if overlaps any previous [t0, t1]
        if any((t0 <= end and t1 >= start) for start, end in used):
            continue

        segment = vol[(vol.index >= t0) & (vol.index <= t1)].copy()
        if segment.empty:
            continue
        segment["delta"] = segment["accumulator"].diff()
        # use 80th percentile as threshold
        thresh = segment["delta"].quantile(0.6)
        ramp = segment[segment["delta"] > thresh]
        if ramp.empty:
            continue

        # exact start/end timestamps & values
        start_ts = ramp.index[0]
        end_ts   = ramp.index[-1]
        start_val = segment.loc[:start_ts]["accumulator"].iloc[-1]
        end_val   = segment.loc[end_ts:]["accumulator"].iloc[0]
        delta     = end_val - start_val

        rows.append({
            "timestamp":    t,
            "valve":        valve,
            "prev_state":   row["prev_state"],
            "state":        row["state"],
            "Start Time":   start_ts,
            "End Time":     end_ts,
            "Start (gal)":  start_val,
            "End (gal)":    end_val,
            "Δ (gal)":      delta,
        })
        used.append((t0, t1))

    return pd.DataFrame(rows)
