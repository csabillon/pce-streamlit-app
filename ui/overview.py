# ui/overview.py

import streamlit as st
import pandas as pd
import plotly.express as px

FLOW_CATEGORY_ORDER = ["Low", "Mid", "High"]
PIE_SIZE = 300
BOX_SIZE = 300
SMALL_MARGIN = dict(l=20, r=20, t=40, b=20)

def render_overview(
    df: pd.DataFrame,
    vol_df: pd.DataFrame,
    plotly_template: str,
    grafana_colors: dict,  # {"OPEN":"#7EB26D","CLOSE":"#E24D42"}
):
    st.header("Pods Overview")

    # ── Keep only Blue & Yellow Pods ──────────────────────────────────────
    df2 = df[df["Active Pod"].isin(["Blue Pod", "Yellow Pod"])].copy()

    # ── Normalize timestamp once ──────────────────────────────────────────
    vol = vol_df.copy()
    if "timestamp" in vol.columns:
        ts = pd.to_datetime(vol["timestamp"])
    elif isinstance(vol.index, pd.DatetimeIndex):
        ts = vol.index.to_series().reset_index(drop=True)
    else:
        vol = vol.reset_index()
        ts = pd.to_datetime(vol.iloc[:, 0])
    vol = vol.reset_index(drop=True)
    vol["timestamp"] = ts
    vol = vol[vol["Active Pod"].isin(["Blue Pod", "Yellow Pod"])]

    # ── Compute totals ────────────────────────────────────────────────────
    vol = vol.sort_values("timestamp")
    vol["time_diff"] = vol["timestamp"].diff().dt.total_seconds().fillna(0)
    vol["pod_prev"] = vol["Active Pod"].shift().fillna(vol["Active Pod"])
    time_by_pod = (
        vol.groupby("pod_prev")["time_diff"]
           .sum().reset_index()
           .rename(columns={"pod_prev":"Pod","time_diff":"Time_Sec"})
    )
    time_by_pod["Time_Min"] = (time_by_pod["Time_Sec"] / 60).round(1)
    total_min = time_by_pod["Time_Min"].sum()

    flow_by_pod = (
        df2.groupby("Active Pod")["Δ (gal)"]
           .sum().reset_index()
           .rename(columns={"Active Pod":"Pod","Δ (gal)":"Flow_Gal"})
    )
    flow_by_pod["Flow_Gal"] = flow_by_pod["Flow_Gal"].round(1)
    total_gal = flow_by_pod["Flow_Gal"].sum()

    # ── Top row: Donut pies + boxplots ────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    # Time Utilization Pie
    with c1:
        fig_time = px.pie(
            time_by_pod, names="Pod", values="Time_Min", hole=0.5,
            title=f"Time Utilization (Total {total_min} min)",
            color="Pod",
            color_discrete_map={"Blue Pod":"#6E8CC8","Yellow Pod":"#F9E79F"},
            template=plotly_template,
            height=PIE_SIZE, width=PIE_SIZE,
        )
        fig_time.update_traces(
            domain=dict(x=[0.15,0.85], y=[0.15,0.85]),
            textinfo="value+percent",
            textposition="outside",
            automargin=True,
        )
        fig_time.update_layout(legend_title_text="Pod", margin=SMALL_MARGIN)
        st.plotly_chart(fig_time, use_container_width=True)

    # Flow Utilization Pie
    with c2:
        fig_flow = px.pie(
            flow_by_pod, names="Pod", values="Flow_Gal", hole=0.5,
            title=f"Flow Utilization (Total {total_gal} gal)",
            color="Pod",
            color_discrete_map={"Blue Pod":"#6E8CC8","Yellow Pod":"#F9E79F"},
            template=plotly_template,
            height=PIE_SIZE, width=PIE_SIZE,
        )
        fig_flow.update_traces(
            domain=dict(x=[0.15,0.85], y=[0.15,0.85]),
            textinfo="value+percent",
            textposition="outside",
            automargin=True,
        )
        fig_flow.update_layout(legend_title_text="Pod", margin=SMALL_MARGIN)
        st.plotly_chart(fig_flow, use_container_width=True)

    # Δ (gal) Boxplot
    with c3:
        fig_delta = px.box(
            df2.assign(**{"Flow Category": pd.Categorical(
                df2["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
            )}),
            x="Active Pod", y="Δ (gal)", color="state",
            title="Δ (gal) Boxplot",
            template=plotly_template,
            category_orders={"Active Pod":["Blue Pod","Yellow Pod"],"state":["OPEN","CLOSE"]},
            color_discrete_map=grafana_colors,
            height=BOX_SIZE, width=BOX_SIZE,
        )
        fig_delta.update_layout(margin=SMALL_MARGIN, showlegend=True)
        st.plotly_chart(fig_delta, use_container_width=True)

    # Max Pressure Boxplot
    with c4:
        fig_pr = px.box(
            df2.assign(**{"Flow Category": pd.Categorical(
                df2["Flow Category"], categories=FLOW_CATEGORY_ORDER, ordered=True
            )}),
            x="Active Pod", y="Max Pressure", color="state",
            title="Max Pressure Boxplot",
            template=plotly_template,
            category_orders={"Active Pod":["Blue Pod","Yellow Pod"],"state":["OPEN","CLOSE"]},
            color_discrete_map=grafana_colors,
            height=BOX_SIZE, width=BOX_SIZE,
        )
        fig_pr.update_layout(margin=SMALL_MARGIN, showlegend=True)
        st.plotly_chart(fig_pr, use_container_width=True)

    st.markdown("---")

    # ── Bottom: Blue / spacer / Yellow ─────────────────────────────────────
    left_col, spacer_col, right_col = st.columns([1, 0.02, 1])

    # Draw the vertical line in the spacer
    with spacer_col:
        line_height = BOX_SIZE + SMALL_MARGIN["t"] + SMALL_MARGIN["b"]
        st.markdown(
            f'<div style="border-left:1px solid #ddd; height:{line_height}px; margin-top:10px;"></div>',
            unsafe_allow_html=True,
        )

    # Blue Pod section
    with left_col:
        st.subheader("Blue Pod")
        bo, bc = st.columns(2)
        with bo:
            fig_bo = px.scatter(
                df2.query('`Active Pod`=="Blue Pod" and state=="OPEN"'),
                x="Δ (gal)", y="Max Pressure",
                trendline="ols",
                title="OPEN – Pressure vs Δ (gal)",
                template=plotly_template,
                color_discrete_sequence=[grafana_colors["OPEN"]],
                height=BOX_SIZE, width=BOX_SIZE,
            )
            fig_bo.update_layout(margin=SMALL_MARGIN, showlegend=False)
            st.plotly_chart(fig_bo, use_container_width=True)
        with bc:
            fig_bc = px.scatter(
                df2.query('`Active Pod`=="Blue Pod" and state=="CLOSE"'),
                x="Δ (gal)", y="Max Pressure",
                trendline="ols",
                title="CLOSE – Pressure vs Δ (gal)",
                template=plotly_template,
                color_discrete_sequence=[grafana_colors["CLOSE"]],
                height=BOX_SIZE, width=BOX_SIZE,
            )
            fig_bc.update_layout(margin=SMALL_MARGIN, showlegend=False)
            st.plotly_chart(fig_bc, use_container_width=True)

    # Yellow Pod section
    with right_col:
        st.subheader("Yellow Pod")
        yo, yc = st.columns(2)
        with yo:
            fig_yo = px.scatter(
                df2.query('`Active Pod`=="Yellow Pod" and state=="OPEN"'),
                x="Δ (gal)", y="Max Pressure",
                trendline="ols",
                title="OPEN – Pressure vs Δ (gal)",
                template=plotly_template,
                color_discrete_sequence=[grafana_colors["OPEN"]],
                height=BOX_SIZE, width=BOX_SIZE,
            )
            fig_yo.update_layout(margin=SMALL_MARGIN, showlegend=False)
            st.plotly_chart(fig_yo, use_container_width=True)
        with yc:
            fig_yc = px.scatter(
                df2.query('`Active Pod`=="Yellow Pod" and state=="CLOSE"'),
                x="Δ (gal)", y="Max Pressure",
                trendline="ols",
                title="CLOSE – Pressure vs Δ (gal)",
                template=plotly_template,
                color_discrete_sequence=[grafana_colors["CLOSE"]],
                height=BOX_SIZE, width=BOX_SIZE,
            )
            fig_yc.update_layout(margin=SMALL_MARGIN, showlegend=False)
            st.plotly_chart(fig_yc, use_container_width=True)
