# ui/charts.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from logic.preprocessing import downsample_for_display

from utils.colors import BY_COLORS, FLOW_COLORS, FLOW_CATEGORY_ORDER

PIE_SIZE = 250
BAR_SIZE = 250
SMALL_MARGIN = dict(l=20, r=20, t=40, b=20)


def plot_open_close_pie_bar(df, flow_colors=FLOW_COLORS):
    """Returns: pie_open, bar_open, pie_close, bar_close"""
    def make_pie_bar(subset, state):
        subset = subset.copy()
        subset["Flow Category"] = pd.Categorical(
            subset["Flow Category"],
            categories=FLOW_CATEGORY_ORDER,
            ordered=True,
        )
        counts = (
            subset
            .groupby("Flow Category", observed=True)
            .size()
            .reindex(FLOW_CATEGORY_ORDER, fill_value=0)
            .reset_index(name="Count")
        )
        pie = px.pie(
            counts,
            names="Flow Category",
            values="Count",
            hole=0.5,
            title=f"{state} – Utilization",
            color="Flow Category",
            category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
            color_discrete_map=flow_colors,
            height=PIE_SIZE,
            width=PIE_SIZE,
        )
        pie.update_traces(
            textinfo="value+percent",
            textposition="outside",
            automargin=True,
        )
        pie.update_layout(legend_title_text="Flow Category", margin=SMALL_MARGIN)

        volume = (
            subset
            .groupby("Flow Category", observed=True)["Δ (gal)"]
            .sum()
            .reindex(FLOW_CATEGORY_ORDER, fill_value=0)
            .reset_index(name="Δ (gal)")
        )
        bar = px.bar(
            volume,
            x="Flow Category",
            y="Δ (gal)",
            title=f"{state} – Δ (gal) Flow Volume",
            color="Flow Category",
            category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
            color_discrete_map=flow_colors,
            height=BAR_SIZE,
            width=BAR_SIZE,
        )
        bar.update_layout(showlegend=False, margin=SMALL_MARGIN)

        return pie, bar

    open_sub  = df[df["state"] == "OPEN"]
    close_sub = df[df["state"] == "CLOSE"]
    return make_pie_bar(open_sub, "OPEN") + make_pie_bar(close_sub, "CLOSE")


def plot_boxplots(df, flow_colors=FLOW_COLORS, template="plotly"):
    """Δ (gal) boxplots for OPEN and CLOSE."""
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )

    def mk_box(sub_df, title):
        fig = px.box(
            sub_df,
            x="Flow Category",
            y="Δ (gal)",
            title=title,
            template=template,
            category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
            color="Flow Category",
            color_discrete_map=flow_colors,
            height=BAR_SIZE,
            width=BAR_SIZE,
        )
        fig.update_layout(margin=SMALL_MARGIN)
        return fig

    return (
        mk_box(d[d["state"] == "OPEN"],  "OPEN – Δ (gal) Boxplot"),
        mk_box(d[d["state"] == "CLOSE"], "CLOSE – Δ (gal) Boxplot"),
    )


def plot_pressure_boxplots(df, flow_colors=FLOW_COLORS, template="plotly"):
    """Max Pressure boxplots for OPEN and CLOSE by flow category."""
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )

    def mk_box(sub_df, title):
        fig = px.box(
            sub_df,
            x="Flow Category",
            y="Max Pressure",
            title=title,
            template=template,
            category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
            color="Flow Category",
            color_discrete_map=flow_colors,
            height=BAR_SIZE,
            width=BAR_SIZE,
        )
        fig.update_layout(margin=SMALL_MARGIN)
        return fig

    return (
        mk_box(d[d["state"] == "OPEN"],  "OPEN – Pressure Boxplot"),
        mk_box(d[d["state"] == "CLOSE"], "CLOSE – Pressure Boxplot"),
    )


def plot_scatter_by_flowcategory(df, flow_colors, flow_category_order, template):
    """
    Four scatterplots (OPEN/CLOSE × FlowRate/Δ) colored by Flow Category,
    each with a single overall OLS trendline in grey.
    Returns (open_fr, open_delta, close_fr, close_delta).
    """
    def mk_trace(sub_df, x, y, title):
        fig = px.scatter(
            sub_df,
            x=x,
            y=y,
            title=title,
            color="Flow Category",
            category_orders={"Flow Category": flow_category_order},
            color_discrete_map=flow_colors,
            template=template,
            trendline="ols",
            trendline_scope="overall",
            trendline_color_override="#696969",
            height=300,
            width=300,
        )
        # rename the single trendline trace
        fig.update_traces(selector=dict(mode="lines"), name="Trend")
        fig.update_layout(margin=SMALL_MARGIN)
        return fig

    open_sub  = df[df["state"] == "OPEN"]
    close_sub = df[df["state"] == "CLOSE"]

    return (
        mk_trace(open_sub,  "Flow Rate (gpm)", "Max Pressure", "OPEN – Pressure vs Flow Rate (gpm)"),
        mk_trace(open_sub,  "Δ (gal)",         "Max Pressure", "OPEN – Pressure vs Δ (gal)"),
        mk_trace(close_sub, "Flow Rate (gpm)", "Max Pressure", "CLOSE – Pressure vs Flow Rate (gpm)"),
        mk_trace(close_sub, "Δ (gal)",         "Max Pressure", "CLOSE – Pressure vs Δ (gal)"),
    )



def plot_accumulator(vol_df, template="plotly"):
    """Plot accumulator gallons over time as lines, colored by Active Pod, DOWNSAMPLED for display."""
    df = vol_df.reset_index().rename(columns={"index": "timestamp"}).copy()
    # Downsample ONLY for visualization; calculations use full data!
    df = downsample_for_display(df, target_points=4000)
    df["segment"] = (df["Active Pod"] != df["Active Pod"].shift()).cumsum()
    pod_colors = BY_COLORS

    fig = go.Figure()
    for _, seg in df.groupby("segment", sort=False):
        pod = seg["Active Pod"].iloc[0]
        fig.add_trace(
            go.Scatter(
                x=seg["timestamp"],
                y=seg["accumulator"],
                mode="lines",
                line=dict(color=pod_colors.get(pod, "#999999"), width=2),
                showlegend=False,
            )
        )

    fig.update_layout(
        title=f"Accumulator Gallons Over Time",
        template=template,
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def plot_time_series(sub_df, template="plotly", oc_colors=None):
    """Two-row time series for Max Pressure and Δ (gal), colored by OPEN/CLOSE."""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Max Pressure Over Time", "Δ (gal) Over Time"),
    )
    for state in ["OPEN", "CLOSE"]:
        s = sub_df[sub_df["state"] == state]
        color = (oc_colors or {}).get(state, "#999999")
        fig.add_trace(
            go.Scatter(
                x=s["timestamp"], y=s["Max Pressure"],
                mode="markers", name=f"Pressure ({state})",
                marker=dict(color=color),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=s["timestamp"], y=s["Δ (gal)"],
                mode="markers", name=f"Δ (gal) ({state})",
                marker=dict(color=color),
            ),
            row=2, col=1,
        )

    fig.update_layout(height=250, template=template, margin=SMALL_MARGIN)
    return fig
