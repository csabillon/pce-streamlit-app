# ui_components/charts.py

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from logic.preprocessing import downsample_for_display
from utils.colors import BY_COLORS, FLOW_COLORS, FLOW_CATEGORY_ORDER

PIE_SIZE = 250
BAR_SIZE = 250
SMALL_MARGIN = dict(l=20, r=20, t=40, b=20)
CONNECTOR_VALVES = {"LMRP Connector", "Wellhead Connector"}

def get_state_label(valve_name, state):
    if valve_name in CONNECTOR_VALVES:
        if state == "OPEN":
            return "LATCH"
        elif state == "CLOSE":
            return "UNLATCH"
        return state
    else:
        return state

def get_state_filter(df, desired_state):
    if "valve" not in df.columns or "state" not in df.columns:
        return pd.Series([False] * len(df), index=df.index)
    mask = []
    for _, row in df.iterrows():
        val = row["valve"]
        s = row["state"]
        if val in CONNECTOR_VALVES:
            if desired_state == "OPEN" and s == "LATCH":
                mask.append(True)
            elif desired_state == "CLOSE" and s == "UNLATCH":
                mask.append(True)
            else:
                mask.append(False)
        else:
            mask.append(s == desired_state)
    return pd.Series(mask, index=df.index)

def get_chart_title(valve_name, state):
    return get_state_label(valve_name, state)

def plot_open_close_pie_bar(df, flow_colors=FLOW_COLORS):
    valve_name = df["valve"].iloc[0] if not df.empty and "valve" in df.columns else ""
    def make_pie_bar(subset, state):
        if subset is None or subset.empty:
            return go.Figure(), go.Figure()
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
        label = get_chart_title(valve_name, state)
        pie = px.pie(
            counts,
            names="Flow Category",
            values="Count",
            hole=0.5,
            title=f"{label} – Utilization",
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
            title=f"{label} – Δ (gal) Flow Volume",
            color="Flow Category",
            category_orders={"Flow Category": FLOW_CATEGORY_ORDER},
            color_discrete_map=flow_colors,
            height=BAR_SIZE,
            width=BAR_SIZE,
        )
        bar.update_layout(showlegend=False, margin=SMALL_MARGIN)

        return pie, bar

    open_sub  = df[get_state_filter(df, "OPEN")]
    close_sub = df[get_state_filter(df, "CLOSE")]
    return make_pie_bar(open_sub, "OPEN") + make_pie_bar(close_sub, "CLOSE")

def plot_boxplots(df, flow_colors=FLOW_COLORS, template="plotly"):
    valve_name = df["valve"].iloc[0] if not df.empty and "valve" in df.columns else ""
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )

    def mk_box(sub_df, state):
        if sub_df is None or sub_df.empty:
            return go.Figure()
        label = get_chart_title(valve_name, state)
        fig = px.box(
            sub_df,
            x="Flow Category",
            y="Δ (gal)",
            title=f"{label} – Δ (gal) Boxplot",
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
        mk_box(d[get_state_filter(d, "OPEN")],  "OPEN"),
        mk_box(d[get_state_filter(d, "CLOSE")], "CLOSE"),
    )

def plot_pressure_boxplots(df, flow_colors=FLOW_COLORS, template="plotly"):
    valve_name = df["valve"].iloc[0] if not df.empty and "valve" in df.columns else ""
    d = df.copy()
    d["Flow Category"] = pd.Categorical(
        d["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
    )

    def mk_box(sub_df, state):
        if sub_df is None or sub_df.empty:
            return go.Figure()
        label = get_chart_title(valve_name, state)
        fig = px.box(
            sub_df,
            x="Flow Category",
            y="Max Pressure",
            title=f"{label} – Pressure Boxplot",
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
        mk_box(d[get_state_filter(d, "OPEN")],  "OPEN"),
        mk_box(d[get_state_filter(d, "CLOSE")], "CLOSE"),
    )

def plot_scatter_by_flowcategory(df, flow_colors, flow_category_order, template):
    valve_name = df["valve"].iloc[0] if not df.empty and "valve" in df.columns else ""
    def mk_trace(sub_df, x, y, state):
        if sub_df is None or sub_df.empty:
            return go.Figure()
        label = get_chart_title(valve_name, state)
        fig = px.scatter(
            sub_df,
            x=x,
            y=y,
            title=f"{label} – {y} vs {x}",
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
        fig.update_traces(selector=dict(mode="lines"), name="Trend")
        fig.update_layout(margin=SMALL_MARGIN)
        return fig

    open_sub  = df[get_state_filter(df, "OPEN")]
    close_sub = df[get_state_filter(df, "CLOSE")]

    return (
        mk_trace(open_sub,  "Flow Rate (gpm)", "Max Pressure", "OPEN"),
        mk_trace(open_sub,  "Δ (gal)",         "Max Pressure", "OPEN"),
        mk_trace(close_sub, "Flow Rate (gpm)", "Max Pressure", "CLOSE"),
        mk_trace(close_sub, "Δ (gal)",         "Max Pressure", "CLOSE"),
    )

def plot_accumulator(vol_df, template="plotly"):
    df = vol_df.reset_index().rename(columns={"index": "timestamp"}).copy()
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
    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    valve_name = sub_df["valve"].iloc[0] if not sub_df.empty and "valve" in sub_df.columns else ""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Max Pressure Over Time", "Δ (gal) Over Time"),
    )
    for state in ["OPEN", "CLOSE"]:
        s = sub_df[get_state_filter(sub_df, state)]
        color = (oc_colors or {}).get(state, "#999999")
        label = get_chart_title(valve_name, state)
        fig.add_trace(
            go.Scatter(
                x=s["timestamp"], y=s["Max Pressure"],
                mode="markers", name=f"Pressure ({label})",
                marker=dict(color=color),
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=s["timestamp"], y=s["Δ (gal)"],
                mode="markers", name=f"Δ (gal) ({label})",
                marker=dict(color=color),
            ),
            row=2, col=1,
        )
    fig.update_layout(height=250, template=template, margin=SMALL_MARGIN)
    return fig
