from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events import plotly_events

from logic.analog_trends_loader import load_analog_map, build_tag
from logic.data_loaders import get_raw_df
from logic.preprocessing import to_ms, downsample_for_display


ABBREVIATIONS = {
    "Regulator": "Reg",
    "Temperature": "Temp",
    "Readback": "RB",
    "Inclinometer": "Inc",
    "Direction": "Dir",
    "Hydrostatic": "Hyd",
    "Solenoid": "Sol",
}


def _abbreviate(label: str) -> str:
    for full, short in ABBREVIATIONS.items():
        label = label.replace(full, short)
    return label


def _shorten(label: str, max_chars: int = 60) -> str:
    """Return label truncated to ``max_chars`` with ellipsis."""
    return label if len(label) <= max_chars else label[: max_chars - 1] + "…"

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
    display_map: dict[int, str] = {}
    if mapping_df is not None and not mapping_df.empty:
        label_map: dict[int, str] = {}
        for _, row in mapping_df.iterrows():
            ch = int(row.get("Ch"))
            name = str(row.get("Analog Name", "") or "").strip()
            label_map[ch] = f"{ch} - {name}" if name else f"{ch}"
            short = _shorten(_abbreviate(name)) if name else ""
            display_map[ch] = f"{ch} - {short}" if short else f"{ch}"
        options = list(label_map.keys())
        channels = st.multiselect(
            "Select Analogs", options, format_func=lambda c: display_map.get(c, str(c))
        )
    else:
        options = list(range(1, 65))
        channels = st.multiselect("Select Channels", options)
        label_map = {ch: str(ch) for ch in options}
        display_map = label_map.copy()

    return channels, label_map, display_map


def render_analog_trends(rig: str, default_start: datetime, default_end: datetime, template: str):
    """Render the Analog Trends page."""

    st.header("Analog Trends")

    st.markdown(
        """
        <style>
        .stMultiSelect [data-baseweb="tag"]{max-width:800px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    start_date, end_date = _get_date_range(default_start, default_end)
    channels, _, display_map = _select_channels(rig)

    graph_type = st.selectbox("Graph Type", ["Line", "Scatter", "Area"])
    dual_axis = st.checkbox("Use dual Y axes", value=False)
    align_method = st.selectbox(
        "Table Alignment", ["Resample to 1s", "Outer join and fill"], index=0
    )

    left_channels: list[int] = []
    right_channels: list[int] = []
    if dual_axis and channels:
        half = max(1, len(channels) // 2)
        left_channels = st.multiselect(
            "Left Axis Analogs",
            channels,
            default=channels[:half],
            format_func=lambda c: display_map.get(c, str(c)),
        )
        remaining = [ch for ch in channels if ch not in left_channels]
        right_channels = st.multiselect(
            "Right Axis Analogs",
            remaining,
            default=remaining,
            format_func=lambda c: display_map.get(c, str(c)),
        )
        channels = sorted(set(left_channels + right_channels))
    else:
        left_channels = channels

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
        display_name = display_map.get(ch, str(ch))
        df = df.rename(columns={df.columns[0]: display_name})
        df.index = pd.to_datetime(df.index)
        if align_method == "Resample to 1s":
            df = df.resample("1s").ffill().bfill()
        frames.append(df)

    if not frames:
        st.warning("No data returned for selected channels.")
        return

    table_df = pd.concat(frames, axis=1)
    if align_method != "Resample to 1s":
        table_df = table_df.sort_index().ffill().bfill()
    chart_df_wide = downsample_for_display(table_df)
    chart_df = chart_df_wide.reset_index().rename(columns={"index": "timestamp"})

    if dual_axis and len(chart_df_wide.columns) > 0:
        mode_map = {"Line": "lines", "Scatter": "markers", "Area": "lines"}
        fig = go.Figure()
        fig.update_layout(template=template)
        x_vals = chart_df_wide.index
        left_cols = [display_map.get(ch, str(ch)) for ch in left_channels]
        right_cols = [display_map.get(ch, str(ch)) for ch in right_channels]
        for col in left_cols:
            if col in chart_df_wide.columns:
                trace_kwargs = dict(
                    x=x_vals,
                    y=chart_df_wide[col],
                    name=col,
                    mode=mode_map[graph_type],
                )
                if graph_type == "Area":
                    trace_kwargs["fill"] = "tozeroy"
                fig.add_trace(go.Scatter(**trace_kwargs))
        for col in right_cols:
            if col in chart_df_wide.columns:
                trace_kwargs = dict(
                    x=x_vals,
                    y=chart_df_wide[col],
                    name=col,
                    mode=mode_map[graph_type],
                    yaxis="y2",
                )
                if graph_type == "Area":
                    trace_kwargs["fill"] = "tozeroy"
                fig.add_trace(go.Scatter(**trace_kwargs))
        fig.update_layout(
            yaxis=dict(title=", ".join(left_cols) if left_cols else None),
            yaxis2=dict(
                title=", ".join(right_cols) if right_cols else None,
                overlaying="y",
                side="right",
            ),
        )
    else:
        melt_df = chart_df.melt(id_vars="timestamp", var_name="channel", value_name="value")
        if graph_type == "Line":
            fig = px.line(melt_df, x="timestamp", y="value", color="channel", template=template)
        elif graph_type == "Scatter":
            fig = px.scatter(melt_df, x="timestamp", y="value", color="channel", template=template)
        else:  # Area
            fig = px.area(melt_df, x="timestamp", y="value", color="channel", template=template)

    events = plotly_events(fig, select_event=True, key="analog_trend_plot")

    x_start = table_df.index.min()
    x_end = table_df.index.max()
    if events:
        ev = events[-1]
        xr = ev.get("range", {}).get("x")
        if xr and len(xr) == 2:
            x_start = pd.to_datetime(xr[0])
            x_end = pd.to_datetime(xr[1])

    stats = table_df.loc[x_start:x_end].agg(["mean", "max", "min"]).T
    stats = stats.rename(columns={"mean": "Mean", "max": "Max", "min": "Min"})
    st.dataframe(stats)

    if st.checkbox("Show Data Table"):
        table_download = table_df.reset_index().rename(columns={"index": "timestamp"})
        st.dataframe(table_download, use_container_width=True)
        csv = table_download.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "analog_trends.csv", "text/csv")

