# ui/analog_trends.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.themes import get_plotly_template
from logic.analog_trends_loader import load_analog_map, build_tag
from logic.data_loaders import get_raw_df


# ---------- helpers ----------
def _to_date(x):
    if x is None:
        return None
    t = pd.to_datetime(x, errors="coerce")
    return None if pd.isna(t) else pd.Timestamp(t.date())

def _to_ms_utc(ts):
    t = pd.to_datetime(ts, errors="coerce")
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return int(t.timestamp() * 1000)

def _normalize_timeseries_df(obj) -> pd.DataFrame:
    if obj is None:
        return pd.DataFrame(columns=["timestamp", "value"])
    if isinstance(obj, pd.Series):
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(obj.index, utc=True, errors="coerce"),
            "value": pd.to_numeric(obj.values, errors="coerce"),
        })
        return df.dropna(subset=["timestamp", "value"]).sort_values("timestamp")

    df = obj.copy()
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "value"])

    if pd.api.types.is_datetime64_any_dtype(df.index):
        df = df.reset_index().rename(columns={df.index.name or "index": "timestamp"})

    lower = {c.lower(): c for c in df.columns}
    ts_col = next((lower[c] for c in ("timestamp","time","datetime","date","ts") if c in lower), None)
    if ts_col is None:
        ts_col = next((c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])), None)
    if ts_col is None:
        ts_col = next((c for c in df.columns if "time" in c.lower() or "date" in c.lower()), None)
    if ts_col is None:
        return pd.DataFrame(columns=["timestamp","value"])

    val_col = next((lower[c] for c in ("value","val","y","v") if c in lower), None)
    if val_col is None:
        val_col = next((c for c in df.columns if c != ts_col and pd.api.types.is_numeric_dtype(df[c])), None)
    if val_col is None:
        return pd.DataFrame(columns=["timestamp","value"])

    d = df[[ts_col, val_col]].rename(columns={ts_col:"timestamp", val_col:"value"})

    if pd.api.types.is_numeric_dtype(d["timestamp"]):
        s = pd.to_numeric(d["timestamp"], errors="coerce")
        m = s.max()
        unit = "ns" if m>1e16 else "ms" if m>1e12 else "s" if m>1e10 else "ms"
        d["timestamp"] = pd.to_datetime(s, unit=unit, utc=True, errors="coerce")
    else:
        d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True, errors="coerce")

    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    return d.dropna(subset=["timestamp","value"]).sort_values("timestamp")


# ---------- LTTB downsampling ----------
def _lttb(x: np.ndarray, y: np.ndarray, n_out: int) -> np.ndarray:
    N = x.size
    if n_out >= N or n_out < 3:
        return np.arange(N)
    bucket = (N - 2) / (n_out - 2)
    idx = np.zeros(n_out, dtype=np.int64)
    idx[0], idx[-1] = 0, N - 1
    a = 0
    for i in range(1, n_out - 1):
        L = int(np.floor((i - 1) * bucket)) + 1
        R = min(int(np.floor(i * bucket)) + 1, N - 1)
        bx, by = x[L:R], y[L:R]
        if bx.size == 0:
            idx[i] = a
            continue
        nL = int(np.floor(i * bucket)) + 1
        nR = min(int(np.floor((i + 1) * bucket)) + 1, N)
        cx = np.mean(x[nL:nR]) if nL < nR else x[-1]
        cy = np.mean(y[nL:nR]) if nL < nR else y[-1]
        ax, ay = x[a], y[a]
        area = np.abs((ax - cx) * (by - ay) - (ay - cy) * (bx - ax))
        a = L + int(np.argmax(area))
        idx[i] = a
    return idx

def _downsample_lttb(df: pd.DataFrame, channel_col: str, max_pts: int = 15000) -> pd.DataFrame:
    if df.empty:
        return df
    parts = []
    for ch, g in df.groupby(channel_col, dropna=False):
        g = g.sort_values("timestamp")
        if len(g) <= max_pts:
            parts.append(g)
            continue
        x = g["timestamp"].astype("int64", copy=False).to_numpy()
        y = g["value"].to_numpy(float)
        keep = _lttb(x, y, max_pts)
        parts.append(g.iloc[keep].copy())
    return pd.concat(parts, ignore_index=True) if parts else df


# ---------- tables & summary ----------
def _table_align_timestamps(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    wide = (
        raw_df.pivot_table(index="timestamp", columns="channel", values="value", aggfunc="mean")
        .sort_index()
    )
    wide = wide.ffill().bfill()
    return wide.reset_index()

def _table_align_1s(raw_df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if raw_df.empty:
        return pd.DataFrame()
    full = pd.date_range(start=start, end=end, freq="1s", tz="UTC")
    wide = None
    for ch, g in raw_df.groupby("channel", dropna=False):
        s = g.set_index("timestamp")["value"].sort_index()
        s = s.reindex(full).ffill().bfill()
        col = s.rename(ch).to_frame()
        wide = col if wide is None else wide.join(col, how="outer")
    wide = wide.ffill().bfill()
    return wide.reset_index().rename(columns={"index": "timestamp"})

def _summary_full_range(wide_df: pd.DataFrame) -> pd.DataFrame:
    if wide_df is None or wide_df.empty:
        return pd.DataFrame(columns=["channel", "Mean", "Median", "Max", "Min", "Std", "Count"])
    df = wide_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    cols = [c for c in df.columns if c != "timestamp" and pd.api.types.is_numeric_dtype(df[c])]
    if not cols:
        return pd.DataFrame(columns=["channel", "Mean", "Median", "Max", "Min", "Std", "Count"])
    stats = df[cols].agg(["mean", "median", "max", "min", "std", "count"]).T.reset_index()
    stats.columns = ["channel", "Mean", "Median", "Max", "Min", "Std", "Count"]
    return stats


# ---------- page ----------
def render_analog_trends(rig: str, default_start=None, default_end=None, template=None) -> None:
    st.title("Analog Trends")

    # keep chevrons (Clear all). Just trim some internal padding.
    st.markdown(
        """
        <style>
          div[data-baseweb="select"] > div { padding-right: 6px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # thin options panel
    left, right = st.columns([0.12, 0.88], gap="small")

    if default_end is None:
        default_end = pd.Timestamp.utcnow().normalize()
    if default_start is None:
        default_start = pd.Timestamp(default_end) - pd.Timedelta(days=60)

    with left:
        st.subheader("Options")

        # Date handling: require both dates
        trend_input = st.date_input(
            "Trend Date Range",
            value=(_to_date(default_start), _to_date(default_end)),
            key="analog_trend_dates",
        )
        valid_dates = isinstance(trend_input, (list, tuple)) and len(trend_input) == 2 and all(trend_input)
        if not valid_dates:
            st.info("Select both start and end dates to load data.")
            st.selectbox("Graph Type", ["Line", "Scatter", "Area"], index=0, key="graph_type_tmp")
            st.checkbox("Use Dual Y Axes", value=False, key="dual_tmp")
            return

        # Time window
        day_start = pd.Timestamp(trend_input[0])
        day_end = pd.Timestamp(trend_input[1])
        if day_end < day_start:
            day_start, day_end = day_end, day_start
        day_end = day_end + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
        sm, em = _to_ms_utc(day_start), _to_ms_utc(day_end)

        graph_type = st.selectbox("Graph Type", ["Line", "Scatter", "Area"], index=0, key="graph_type_main")
        use_dual_y = st.checkbox("Use Dual Y Axes", value=False, key="dual_main")

        # Keys for axis widgets
        left_key = "left_axis_select"
        right_key = "right_axis_select"

        # If dual disabled, clear the axis widget state BEFORE any widgets with those keys are created
        if not use_dual_y:
            st.session_state.pop(left_key, None)
            st.session_state.pop(right_key, None)

        # Build labels (full)
        analog_map = load_analog_map(rig)
        have_map = analog_map is not None and len(analog_map) > 0
        label_to_channel: dict[str, int] = {}

        if have_map:
            analog_map = analog_map.copy()

            def _label_row(r):
                ch = int(r["Ch"])
                name = r.get("Analog Name")
                units = r.get("Units")
                name_str = "" if (name is None or (isinstance(name, float) and pd.isna(name))) else str(name)
                units_str = "" if (units is None or (isinstance(units, float) and pd.isna(units))) else str(units)
                base = f"{ch} · {name_str}" if name_str else f"{ch} · Channel"
                return f"{base} [{units_str}]" if units_str else base

            analog_map["full_label"] = analog_map.apply(_label_row, axis=1)
            for _, r in analog_map.iterrows():
                label_to_channel[r["full_label"]] = int(r["Ch"])
            all_labels = analog_map["full_label"].tolist()
        else:
            st.info("No analog channel map found — select channels directly.")
            all_labels = [f"Ch {n}" for n in range(1, 100)]
            label_to_channel = {lbl: int(lbl.split()[-1]) for lbl in all_labels}

        # Main selection
        sel_key = "select_analogs"
        selected_labels = st.multiselect(
            "Select Analogs",
            options=all_labels,
            default=st.session_state.get(sel_key, []),
            key=sel_key,
        )

        # Axis selectors only when dual is enabled and we have selections
        if use_dual_y and selected_labels:
            # compute clean defaults BEFORE widgets
            prev_left = [x for x in st.session_state.get(left_key, []) if x in selected_labels]
            prev_right = [x for x in st.session_state.get(right_key, []) if x in selected_labels]

            if not prev_left and not prev_right:
                mid = max(1, len(selected_labels) // 2)
                prev_left = selected_labels[:mid]
                prev_right = selected_labels[mid:] or [selected_labels[-1]]

            # favor left on overlap
            overlap = set(prev_left) & set(prev_right)
            if overlap:
                prev_right = [x for x in prev_right if x not in overlap]

            # render widgets with cleaned defaults; DO NOT write to session_state after
            left_labels = st.multiselect(
                "Left Y Axis",
                options=selected_labels,
                default=prev_left,
                key=left_key,
            )
            right_labels = st.multiselect(
                "Right Y Axis",
                options=selected_labels,
                default=prev_right,
                key=right_key,
            )
        else:
            left_labels, right_labels = [], []

    # Nothing selected -> stop
    if not selected_labels:
        with right:
            st.info("Select one or more analogs to plot.")
        return

    # Fetch data
    fetch_list = [(label_to_channel[lbl], lbl) for lbl in selected_labels]
    frames = []
    for ch, label in fetch_list:
        tag = build_tag(rig, int(ch))
        raw = get_raw_df(tag, sm, em)
        norm = _normalize_timeseries_df(raw)
        if not norm.empty:
            norm["channel"] = label
            frames.append(norm)
    raw_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["timestamp","value","channel"])

    # Table & metrics
    display_df = _table_align_timestamps(raw_df) if not raw_df.empty else pd.DataFrame(columns=["timestamp"])
    full_stats = _summary_full_range(display_df)

    with right:
        tpl = template or get_plotly_template()
        plot_df = _downsample_lttb(raw_df, "channel", 15000) if not raw_df.empty else raw_df

        fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])
        fill = "tozeroy" if graph_type == "Area" else None
        show_markers = (graph_type == "Scatter")

        right_set = set(right_labels) if use_dual_y else set()
        for name in plot_df["channel"].dropna().unique():
            sub = plot_df[plot_df["channel"] == name]
            use_right = (name in right_set)
            fig.add_trace(
                go.Scatter(
                    x=sub["timestamp"], y=sub["value"], name=name,
                    mode=("lines+markers" if show_markers else "lines"),
                    fill=fill, connectgaps=True,
                ),
                row=1, col=1, secondary_y=use_right
            )

        fig.update_layout(
            template=tpl,
            height=620,
            margin=dict(l=44, r=60, t=36, b=36),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            uirevision="analog-trends",
        )
        fig.update_xaxes(title_text="timestamp", rangeslider_visible=False)
        fig.update_yaxes(
            title_text="Value (Left)", secondary_y=False,
            showline=True, ticks="outside", automargin=True, title_standoff=12
        )
        if use_dual_y:
            fig.update_yaxes(
                title_text="Value (Right)", secondary_y=True,
                showline=True, ticks="outside", automargin=True, title_standoff=12,
                showticklabels=True
            )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"scrollZoom": True, "doubleClick": "reset"},
        )

        st.markdown("### Key Metrics")
        if not full_stats.empty:
            num_cols = ["Mean", "Median", "Max", "Min", "Std", "Count"]
            for c in num_cols:
                if c in full_stats.columns:
                    full_stats[c] = pd.to_numeric(full_stats[c], errors="coerce").round(3)
            st.dataframe(full_stats, use_container_width=True, hide_index=True)
        else:
            st.info("No data available for the selected date range.")

        st.markdown("---")
        st.markdown("### Table")
        align_choice = st.selectbox(
            "Table Alignment",
            options=["Align to timestamps", "Resample to 1s (ffill/bfill)", "No alignment"],
            index=0,
        )
        if not raw_df.empty:
            if align_choice.startswith("Align to timestamps"):
                display_df = _table_align_timestamps(raw_df)
            elif align_choice.startswith("Resample to 1s"):
                display_df = _table_align_1s(raw_df, day_start.tz_localize("UTC"), day_end.tz_localize("UTC"))
            else:
                display_df = _table_align_timestamps(raw_df)

        st.dataframe(display_df, use_container_width=True, hide_index=True)
