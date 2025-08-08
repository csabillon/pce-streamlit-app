from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

from logic.analog_trends_loader import load_analog_map, build_tag
from logic.data_loaders import get_raw_df
from logic.preprocessing import to_ms, downsample_for_display


def _get_date_range(default_start: datetime, default_end: datetime):
    """Render and return the date range selector for the trends page."""

    value = st.date_input(
        "Trend Date Range",
        value=(default_start, default_end),
        key="analog_trend_dates",
    )

    if isinstance(value, (list, tuple)) and len(value) == 2:
        return value[0], value[1]
    return value, value


def _select_channels(rig: str):
    """Return list of selected channel numbers and mapping to labels."""

    mapping_df = load_analog_map(rig)
    if mapping_df is not None and not mapping_df.empty:
        options = []
        label_map: dict[int, str] = {}
        for _, row in mapping_df.iterrows():
            ch = int(row.get("Ch"))
            name = str(row.get("Analog Name", "") or "").strip()
            label = f"{ch} - {name}" if name else f"{ch}"
            options.append(label)
            label_map[ch] = label
        selected_labels = st.multiselect("Select Analogs", options)
        channels = [int(lbl.split(" - ")[0]) for lbl in selected_labels]
    else:
        options = [str(i) for i in range(1, 65)]
        selected_labels = st.multiselect("Select Channels", options)
        channels = [int(x) for x in selected_labels]
        label_map = {ch: str(ch) for ch in channels}

    return channels, label_map


def render_analog_trends(rig: str, default_start: datetime, default_end: datetime, template: str):
    """Render the Analog Trends page."""

    st.header("Analog Trends")

    start_date, end_date = _get_date_range(default_start, default_end)
    channels, label_map = _select_channels(rig)

    graph_type = st.selectbox("Graph Type", ["Line", "Scatter", "Area"])

    if not channels:
        st.info("Select one or more channels to display.")
        return

    sm = to_ms(start_date)
    em = to_ms(end_date + timedelta(days=1)) - 1

    frames = []
    for ch in channels:
        tag = build_tag(rig, ch)
        df = get_raw_df(tag, sm, em)
        if df.empty:
            continue
        df = df.rename(columns={df.columns[0]: "value"})
        df.index = pd.to_datetime(df.index)
        df = downsample_for_display(df)
        df["channel"] = label_map.get(ch, str(ch))
        frames.append(df)

    if not frames:
        st.warning("No data returned for selected channels.")
        return

    chart_df = pd.concat(frames).reset_index().rename(columns={"index": "timestamp"})

    if graph_type == "Line":
        fig = px.line(chart_df, x="timestamp", y="value", color="channel", template=template)
    elif graph_type == "Scatter":
        fig = px.scatter(chart_df, x="timestamp", y="value", color="channel", template=template)
    else:  # Area
        fig = px.area(chart_df, x="timestamp", y="value", color="channel", template=template)

    st.plotly_chart(fig, use_container_width=True)

