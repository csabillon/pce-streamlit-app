# logic/pressure_cycles.py
# ------------------------

import pandas as pd
import numpy as np

def analyze_pressure_cycles(df, valve_map, well_pressure_series):
    """
    For each valve (top-to-bottom order), analyze CLOSE->OPEN intervals where
    no lower valve is closed at any point during the interval.
    For each valid cycle, report duration and well pressure statistics.
    """
    # Ensure proper sort order by timestamp
    stack_order = list(valve_map.keys())
    df = df.copy()
    df = df[df["state"].isin(["OPEN", "CLOSE"])]
    df = df.sort_values("timestamp")

    results = []
    for valve in stack_order:
        sub = df[df["valve"] == valve]
        sub = sub.sort_values("timestamp")
        state_seq = sub["state"].values
        times = pd.to_datetime(sub["timestamp"]).values

        # Find all CLOSE transitions
        close_idxs = np.where(state_seq == "CLOSE")[0]
        for idx in close_idxs:
            close_time = times[idx]
            # Find the next OPEN after this CLOSE for this valve
            open_idxs = np.where((times > close_time) & (state_seq == "OPEN"))[0]
            if len(open_idxs) == 0:
                continue  # No open found; incomplete cycle
            open_time = times[open_idxs[0]]

            # Check all lower valves: must be OPEN throughout [close_time, open_time]
            lower_valves = stack_order[stack_order.index(valve) + 1 :]
            block = False
            for lv in lower_valves:
                # Find the state of the lower valve at close_time
                lower_events = df[(df["valve"] == lv) & (pd.to_datetime(df["timestamp"]) <= close_time)]
                last_state = lower_events.sort_values("timestamp")["state"].values[-1] if not lower_events.empty else "OPEN"
                if last_state == "CLOSE":
                    block = True
                    break
                # If any CLOSE event for the lower valve occurs during the interval, block
                in_window = df[
                    (df["valve"] == lv)
                    & (pd.to_datetime(df["timestamp"]) > close_time)
                    & (pd.to_datetime(df["timestamp"]) < open_time)
                    & (df["state"] == "CLOSE")
                ]
                if not in_window.empty:
                    block = True
                    break
            if block:
                continue  # Skip this cycle

            # Get well pressure during this interval
            interval_press = well_pressure_series.loc[close_time:open_time]
            if interval_press.empty:
                continue

            result = {
                "Valve": valve,
                "Close Time": pd.to_datetime(close_time),
                "Open Time": pd.to_datetime(open_time),
                "Duration (min)": round((pd.to_datetime(open_time) - pd.to_datetime(close_time)).total_seconds() / 60, 2),
                "Min Well Pressure": round(interval_press.min(), 2),
                "Max Well Pressure": round(interval_press.max(), 2),
                "Avg Well Pressure": round(interval_press.mean(), 2),
            }
            results.append(result)

    return pd.DataFrame(results)
