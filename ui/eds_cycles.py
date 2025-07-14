# ui/eds_cycles.py

import streamlit as st
import pandas as pd
from logic.dashboard_data import get_timeseries_data
from datetime import timedelta

EDS_CHANNELS = ["Ba", "Bb", "Ya", "Yb"]
POD_CHANNEL_MAP = {1: "Ba", 2: "Bb", 3: "Ya", 4: "Yb"}

def get_eds_triggers_and_valve_events(
    rig, start, end, valve_map, simple_map, vol_ext, active_pod_tag, eds_base_tag, window_seconds=900
):
    all_triggers = []
    all_valve_events = []
    pod_tag = active_pod_tag  # Use passed tag
    pod_df = get_timeseries_data(pod_tag, start, end)
    vol_df = get_timeseries_data(vol_ext, start, end)
    if not vol_df.empty:
        vol_df['timestamp_dt'] = pd.to_datetime(vol_df['timestamp'])
        vol_df = vol_df.sort_values('timestamp_dt')

    # Gather all EDS triggers (with channel and pod for assignment)
    trigger_list = []
    for ch in EDS_CHANNELS:
        # Build eds_tag depending on rig:
        if rig == "Drillmax":
            eds_tag = f"{eds_base_tag}{ch}EDSProgress"
        else:
            eds_tag = f"{eds_base_tag}{ch}.{ch}EDSProgress"
        
        prog_df = get_timeseries_data(eds_tag, start, end)
        if prog_df.empty:
            continue
        prog_df['timestamp_dt'] = pd.to_datetime(prog_df['timestamp'])
        prog_df = prog_df.sort_values('timestamp_dt')
        prog_df['prev_value'] = prog_df['value'].shift(1).fillna(0)
        triggers = prog_df[(prog_df['prev_value'] == 0) & (prog_df['value'] > 0)].reset_index(drop=True)

        for _, trig_row in triggers.iterrows():
            trigger_time = trig_row['timestamp_dt']
            trigger_val = trig_row['value']
            # Find pod at command time
            pod_row = pod_df[pod_df['timestamp'] <= trigger_time]
            if not pod_row.empty:
                pod_val = int(pod_row.iloc[-1]['value'])
                pod = 'Blue Pod' if pod_val in [1, 2] else 'Yellow Pod'
            else:
                pod_val = None
                pod = 'Unknown'
            if pod_val in POD_CHANNEL_MAP and POD_CHANNEL_MAP[pod_val] == ch:
                trig_val_display = int(trigger_val) if int(trigger_val) == trigger_val else trigger_val
                trigger_list.append({
                    "Channel": ch,
                    "EDS Command Time": trigger_time,
                    "Pod at Command": pod,
                    "EDS Command Value": trig_val_display,
                })

    # Sort triggers by time
    triggers_df = pd.DataFrame(trigger_list)
    if triggers_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    triggers_df = triggers_df.sort_values("EDS Command Time").reset_index(drop=True)
    triggers_df.insert(0, "Event #", triggers_df.index + 1)

    # For each EDS trigger, determine its own window
    total_vols = []
    for i, row in triggers_df.iterrows():
        this_time = row["EDS Command Time"]
        if i + 1 < len(triggers_df):
            next_time = triggers_df.iloc[i + 1]["EDS Command Time"]
            window_end = min(this_time + timedelta(seconds=window_seconds), next_time)
        else:
            window_end = this_time + timedelta(seconds=window_seconds)

        # Flow accumulation: use this window
        total_vol = None
        if not vol_df.empty:
            vol_window = vol_df[
                (vol_df['timestamp_dt'] >= this_time) &
                (vol_df['timestamp_dt'] < window_end)
            ]
            if not vol_window.empty:
                vol_min = vol_window['value'].min()
                vol_max = vol_window['value'].max()
                total_vol = round((vol_max - vol_min) / 10, 2)
        total_vols.append(total_vol)

        # Valve events: only assign those in this window
        for valve_name, tag in valve_map.items():
            valve_df = get_timeseries_data(tag, this_time, window_end)
            if valve_df.empty:
                continue
            valve_df = valve_df.sort_values('timestamp')
            valve_df['prev_value'] = valve_df['value'].shift(1)
            transitions = valve_df[valve_df['value'] != valve_df['prev_value']].dropna().reset_index(drop=True)
            for _, vrow in transitions.iterrows():
                event_time = pd.to_datetime(vrow['timestamp'])
                seconds_after = (event_time - this_time).total_seconds()
                if 0 <= seconds_after < (window_end - this_time).total_seconds():
                    event_type = simple_map.get(int(vrow['value']), "OTHER")
                    status_code = int(vrow['value']) if 'value' in vrow else None
                    all_valve_events.append({
                        "EDS Command Time": this_time,
                        "EDS Command Value": row["EDS Command Value"],
                        "Valve Name": valve_name,
                        "Valve Event": event_type,
                        "Valve Event Time": event_time,
                        "Seconds After Command": int(seconds_after),
                        "Status Code": status_code
                    })

    # Update triggers_df with computed volumes
    triggers_df["Total Volume (gal)"] = total_vols

    valve_events_df = pd.DataFrame(all_valve_events)
    return triggers_df, valve_events_df

def render_eds_cycles(
    rig, start_date, end_date,
    valve_map=None, simple_map=None,
    vol_ext=None, active_pod_tag=None, eds_base_tag=None
):
    cache_key = f"eds_data_{rig}_{start_date}_{end_date}"
    if (cache_key not in st.session_state) or st.button("Reload EDS Data"):
        triggers_df, valve_events_df = get_eds_triggers_and_valve_events(
            rig, start_date, end_date,
            valve_map, simple_map, vol_ext,
            active_pod_tag, eds_base_tag,
            window_seconds=900  # 15 min
        )
        st.session_state[cache_key] = (triggers_df, valve_events_df)
    else:
        triggers_df, valve_events_df = st.session_state[cache_key]

    st.subheader("EDS Command Log")
    if triggers_df.empty:
        st.info("No EDS commands detected in the selected range.")
        return

    show_cols = ["Event #", "EDS Command Time", "Pod at Command", "EDS Command Value", "Total Volume (gal)"]
    st.dataframe(triggers_df[show_cols], use_container_width=True, hide_index=True)

    def format_cmd_row(row):
        t = pd.to_datetime(row["EDS Command Time"]).strftime("%Y-%m-%d %H:%M:%S")
        return f"{row['Event #']}) {t} | {row['Pod at Command']} | Value: {row['EDS Command Value']}"

    st.subheader("Select an EDS Command to View Related Valve Events")
    select_options = ["Show all"] + [
        format_cmd_row(row) for _, row in triggers_df.iterrows()
    ]
    selected_idx = st.selectbox(
        "Choose an EDS Command",
        options=range(len(select_options)),
        format_func=lambda i: select_options[i]
    )

    st.subheader("Valve Events After Selected EDS Command (up to 15 min or next EDS)")
    if selected_idx == 0:
        filtered_events = valve_events_df
    else:
        selected_time = triggers_df.iloc[selected_idx - 1]["EDS Command Time"]
        filtered_events = valve_events_df[valve_events_df["EDS Command Time"] == selected_time]

    if filtered_events.empty:
        st.info("No valve events found after the selected EDS command.")
    else:
        st.dataframe(
            filtered_events[
                [
                    "EDS Command Time",
                    "EDS Command Value",
                    "Valve Name",
                    "Valve Event",
                    "Valve Event Time",
                    "Seconds After Command",
                    "Status Code"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )
