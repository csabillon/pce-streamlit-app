import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

FLOW_CATEGORY_ORDER = ["Low", "Mid", "High"]

# Sizes for the small pies / bars
PIE_SIZE = 300
BAR_SIZE = 300

# Shared margin
SMALL_MARGIN = dict(l=20, r=20, t=40, b=20)

def plot_open_close_pie_bar(df, flow_colors):
    open_sub = df[df["state"] == "OPEN"].copy()
    close_sub = df[df["state"] == "CLOSE"].copy()

    def make_pie_bar(subset, state):
        subset["Flow Category"] = pd.Categorical(
            subset["Flow Category"],
            categories=FLOW_CATEGORY_ORDER,
            ordered=True,
        )
        # --- PIE (counts + % outside) ---
        counts = (
            subset["Flow Category"]
                  .value_counts()
                  .reindex(FLOW_CATEGORY_ORDER, fill_value=0)
                  .reset_index()
        )
        counts.columns = ["Flow Category", "Count"]
        pie = px.pie(
            counts,
            names="Flow Category",
            values="Count",
            hole=0.5,
            title=f"{state} – Utilization",
            color="Flow Category",
            category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
            color_discrete_map=flow_colors,
            height=PIE_SIZE,
            width=PIE_SIZE,
        )
        pie.update_traces(
            textinfo="value+percent",
            textposition="outside",
            insidetextorientation="horizontal",
            automargin=True,
        )
        pie.update_layout(legend_title_text="Flow Category", margin=SMALL_MARGIN)

        # --- BAR (Δ flow volume) ---
        volume = (
            subset
            .groupby("Flow Category", observed=True)["Δ (gal)"]
            .sum()
            .reindex(FLOW_CATEGORY_ORDER, fill_value=0)
            .reset_index()
        )
        bar = px.bar(
            volume,
            x="Flow Category",
            y="Δ (gal)",
            title=f"{state} – Δ (gal) Flow Volume",
            color="Flow Category",
            category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
            color_discrete_map=flow_colors,
            height=BAR_SIZE,
            width=BAR_SIZE,
        )
        bar.update_layout(showlegend=False, margin=SMALL_MARGIN)

        return pie, bar

    return make_pie_bar(open_sub, "OPEN") + make_pie_bar(close_sub, "CLOSE")


def plot_boxplots(df, flow_colors, template):
    """Δ (gal) boxplots for OPEN/CLOSE."""
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )
    open_df = d[d["state"] == "OPEN"]
    close_df = d[d["state"] == "CLOSE"]

    box_open = px.box(
        open_df, x="Flow Category", y="Δ (gal)",
        title="OPEN – Δ (gal) Boxplot",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color="Flow Category",
        color_discrete_map=flow_colors,
        height=BAR_SIZE, width=BAR_SIZE,
    )
    box_open.update_layout(margin=SMALL_MARGIN)

    box_close = px.box(
        close_df, x="Flow Category", y="Δ (gal)",
        title="CLOSE – Δ (gal) Boxplot",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color="Flow Category",
        color_discrete_map=flow_colors,
        height=BAR_SIZE, width=BAR_SIZE,
    )
    box_close.update_layout(margin=SMALL_MARGIN)

    return box_open, box_close


def plot_pressure_boxplots(df, flow_colors, template):
    """Pressure boxplots for OPEN/CLOSE by flow category."""
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )
    open_df = d[d["state"] == "OPEN"]
    close_df = d[d["state"] == "CLOSE"]

    box_open = px.box(
        open_df, x="Flow Category", y="Max Pressure (±30s)",
        title="OPEN – Pressure Boxplot",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color="Flow Category",
        color_discrete_map=flow_colors,
        height=BAR_SIZE, width=BAR_SIZE,
    )
    box_open.update_layout(margin=SMALL_MARGIN)

    box_close = px.box(
        close_df, x="Flow Category", y="Max Pressure (±30s)",
        title="CLOSE – Pressure Boxplot",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color="Flow Category",
        color_discrete_map=flow_colors,
        height=BAR_SIZE, width=BAR_SIZE,
    )
    box_close.update_layout(margin=SMALL_MARGIN)

    return box_open, box_close


def plot_pressure_vs_delta(df, flow_colors, template):
    """
    Legacy: Pressure vs Δ (gal).
    """
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )
    open_df = d[d["state"] == "OPEN"]
    close_df = d[d["state"] == "CLOSE"]

    scatter_open = px.scatter(
        open_df, x="Δ (gal)", y="Max Pressure (±30s)",
        title="OPEN – Pressure vs Δ (gal)",
        color="Flow Category",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color_discrete_map=flow_colors,
        height=PIE_SIZE, width=PIE_SIZE
    )
    scatter_open.update_layout(margin=SMALL_MARGIN)

    scatter_close = px.scatter(
        close_df, x="Δ (gal)", y="Max Pressure (±30s)",
        title="CLOSE – Pressure vs Δ (gal)",
        color="Flow Category",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color_discrete_map=flow_colors,
        height=PIE_SIZE, width=PIE_SIZE
    )
    scatter_close.update_layout(margin=SMALL_MARGIN)

    return scatter_open, scatter_close


def plot_pressure_vs_flowrate(df, flow_colors, template):
    """
    New: Pressure vs event‑average Flow Rate (gpm).
    """
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )
    open_df = d[d["state"] == "OPEN"]
    close_df = d[d["state"] == "CLOSE"]

    scatter_open = px.scatter(
        open_df, x="Flow Rate (gpm)", y="Max Pressure (±30s)",
        title="OPEN – Pressure vs Flow Rate (gpm)",
        color="Flow Category",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color_discrete_map=flow_colors,
        height=PIE_SIZE, width=PIE_SIZE
    )
    scatter_open.update_layout(margin=SMALL_MARGIN)

    scatter_close = px.scatter(
        close_df, x="Flow Rate (gpm)", y="Max Pressure (±30s)",
        title="CLOSE – Pressure vs Flow Rate (gpm)",
        color="Flow Category",
        template=template,
        category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
        color_discrete_map=flow_colors,
        height=PIE_SIZE, width=PIE_SIZE
    )
    scatter_close.update_layout(margin=SMALL_MARGIN)

    return scatter_open, scatter_close


def plot_time_series(sub_df, template, grafana_colors):
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Max Pressure Over Time", "Δ (gal) Over Time"),
    )
    for state in ["OPEN", "CLOSE"]:
        s = sub_df[sub_df["state"] == state]
        fig.add_trace(go.Scatter(
            x=s["timestamp"], y=s["Max Pressure (±30s)"],
            mode="markers", name=f"Pressure ({state})",
            marker=dict(color=grafana_colors[state])
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=s["timestamp"], y=s["Δ (gal)"],
            mode="markers", name=f"Δ (gal) ({state})",
            marker=dict(color=grafana_colors[state])
        ), row=2, col=1)

    fig.update_layout(
        height=600, template=template,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_accumulator(vol_df, template):
    df = vol_df.reset_index().rename(columns={"index": "timestamp"}).copy()
    df["segment"] = (df["Active Pod"] != df["Active Pod"].shift()).cumsum()
    pod_colors = {"Blue Pod": "#1f77b4", "Yellow Pod": "#ffdd57"}

    fig = go.Figure()
    for _, seg in df.groupby("segment", sort=False):
        pod = seg["Active Pod"].iloc[0]
        fig.add_trace(go.Scatter(
            x=seg["timestamp"], y=seg["accumulator"],
            mode="lines",
            line=dict(color=pod_colors.get(pod, "#999999"), width=2),
            showlegend=False,
        ))

    max_pts = 45000
    dur     = (vol_df.index[-1] - vol_df.index[0]).total_seconds()
    interval = f"{max(int(dur / max_pts),1)}s"

    fig.update_layout(
        title=f"Accumulator Gallons Over Time ({interval})",
        template=template,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig
