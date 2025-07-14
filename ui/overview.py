# ui/overview.py

import streamlit as st
import pandas as pd
import plotly.express as px

PIE_SIZE     = 300
BOX_SIZE     = 300
SMALL_MARGIN = dict(l=20, r=20, t=40, b=20)

def render_overview(
    df: pd.DataFrame,
    vol_df: pd.DataFrame,
    plotly_template: str,
    oc_colors: dict,
    by_colors: dict,      
    flow_colors: dict,
    flow_category_order: list,  
):
    st.header("Pods Overview")

    # ── Filter to Blue & Yellow ────────────────────────────────────────────
    df2 = df[df["Active Pod"].isin(["Blue Pod", "Yellow Pod"])].copy()

    # ── Prepare vol_df ────────────────────────────────────────────────────
    vol = vol_df.copy()
    if "timestamp" in vol.columns:
        vol["timestamp"] = pd.to_datetime(vol["timestamp"])
    elif isinstance(vol.index, pd.DatetimeIndex):
        vol = vol.reset_index().rename(columns={vol.index.name or "index": "timestamp"})
        vol["timestamp"] = pd.to_datetime(vol["timestamp"])
    else:
        vol = vol.reset_index().rename(columns={vol.columns[0]: "timestamp"})
        vol["timestamp"] = pd.to_datetime(vol["timestamp"])
    vol = vol[vol["Active Pod"].isin(["Blue Pod", "Yellow Pod"])]

    # ── Compute Time & Flow Utilization ──────────────────────────────────
    vol = vol.sort_values("timestamp")
    vol["time_diff"] = vol["timestamp"].diff().dt.total_seconds().fillna(0)
    vol["pod_prev"]  = vol["Active Pod"].shift().fillna(vol["Active Pod"])
    time_by_pod = (
        vol.groupby("pod_prev")["time_diff"]
           .sum().reset_index()
           .rename(columns={"pod_prev":"Pod","time_diff":"Time_Sec"})
    )
    time_by_pod["Time_Min"] = (time_by_pod["Time_Sec"]/60).round(1)
    total_min = time_by_pod["Time_Min"].sum().round(1)

    flow_by_pod = (
        df2.groupby("Active Pod")["Δ (gal)"]
           .sum().reset_index()
           .rename(columns={"Active Pod":"Pod","Δ (gal)":"Flow_Gal"})
    )
    flow_by_pod["Flow_Gal"] = flow_by_pod["Flow_Gal"].round(1)
    total_gal = flow_by_pod["Flow_Gal"].sum().round(1)

    # ── Top row: Donut pies & boxplots ────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    # Time Utilization Pie
    with c1:
        fig = px.pie(
            time_by_pod, names="Pod", values="Time_Min", hole=0.5,
            title=f"Time Utilization\n(Total {total_min} min)",
            color="Pod",
            color_discrete_map=by_colors,
            template=plotly_template,
            height=PIE_SIZE, width=PIE_SIZE,
        )
        fig.update_traces(
            textinfo="value+percent", textposition="outside",
            domain=dict(x=[0.15,0.85], y=[0.15,0.85]), automargin=True
        )
        fig.update_layout(legend_title_text="Pod", margin=SMALL_MARGIN)
        st.plotly_chart(fig, use_container_width=True)

    # Flow Utilization Pie
    with c2:
        fig = px.pie(
            flow_by_pod, names="Pod", values="Flow_Gal", hole=0.5,
            title=f"Flow Utilization\n(Total {total_gal} gal)",
            color="Pod",
            color_discrete_map=by_colors,
            template=plotly_template,
            height=PIE_SIZE, width=PIE_SIZE,
        )
        fig.update_traces(
            textinfo="value+percent", textposition="outside",
            domain=dict(x=[0.15,0.85], y=[0.15,0.85]), automargin=True
        )
        fig.update_layout(legend_title_text="Pod", margin=SMALL_MARGIN)
        st.plotly_chart(fig, use_container_width=True)

    # Δ (gal) Boxplot
    df2_cat = df2.assign(**{"Flow Category": pd.Categorical(
        df2["Flow Category"], categories=flow_category_order, ordered=True
    )})
    with c3:
        fig = px.box(
            df2_cat, x="Active Pod", y="Δ (gal)", color="state",
            title="Δ (gal) Boxplot",
            template=plotly_template,
            category_orders={
                "Active Pod": ["Blue Pod", "Yellow Pod"],
                "state":      ["OPEN", "CLOSE"],
            },
            color_discrete_map=oc_colors,
            height=BOX_SIZE, width=BOX_SIZE,
        )
        fig.update_layout(margin=SMALL_MARGIN, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # Max Pressure Boxplot
    with c4:
        fig = px.box(
            df2_cat, x="Active Pod", y="Max Pressure", color="state",
            title="Max Pressure Boxplot",
            template=plotly_template,
            category_orders={
                "Active Pod": ["Blue Pod", "Yellow Pod"],
                "state":      ["OPEN", "CLOSE"],
            },
            color_discrete_map=oc_colors,
            height=BOX_SIZE, width=BOX_SIZE,
        )
        fig.update_layout(margin=SMALL_MARGIN, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Bottom row: 3 columns, stacked by Flow Category, total-only labels ──────────────────
    col_blue, col_yellow, col_total = st.columns(3)

    def plot_depletion(pod_name: str, container, df_src: pd.DataFrame):
        # Summarize depletion by valve & flow category
        summary = (
            df_src
            .groupby(["valve", "Flow Category"])["Depletion (%)"]
            .sum().reset_index()
        )
        pivot = (
            summary
            .pivot(index="valve", columns="Flow Category", values="Depletion (%)")
            .fillna(0)
            .reindex(columns=flow_category_order, fill_value=0)
        )

        # Melt for px.bar
        long = pivot.reset_index().melt(
            id_vars="valve", var_name="Flow Category", value_name="Depletion"
        )

        # Build stacked bar chart
        fig = px.bar(
            long,
            y="valve",
            x="Depletion",
            color="Flow Category",
            orientation="h",
            title=pod_name,
            template=plotly_template,
            category_orders={"Flow Category": flow_category_order},
            color_discrete_map=flow_colors,
            text=None,  # no segment labels
        )

        # Add a single annotation per bar: the total depletion
        totals = pivot.sum(axis=1)
        for valve, total in totals.items():
            fig.add_annotation(
                x=total,
                y=valve,
                text=f"{total:.1f}%",
                showarrow=False,
                xanchor="left",
                font=dict(size=12),
            )

        # Dynamic height & layout
        n = pivot.shape[0]
        height = max(BOX_SIZE, n * 40 + 120)
        fig.update_layout(
            height=height,
            margin=dict(l=240, r=20, t=40, b=20),
            showlegend=(pod_name == "Total Depletion by Flow Category"),  # legend only on Total
        )
        fig.update_xaxes(title="Depletion (%)")
        fig.update_yaxes(automargin=True, tickfont=dict(size=12), title="")

        container.plotly_chart(fig, use_container_width=True)

    with col_blue:
        plot_depletion("Blue Pod: Depletion by Flow Category", col_blue, df2[df2["Active Pod"] == "Blue Pod"])
    with col_yellow:
        plot_depletion("Yellow Pod: Depletion by Flow Category", col_yellow, df2[df2["Active Pod"] == "Yellow Pod"])
    with col_total:
        plot_depletion("Total Depletion by Flow Category", col_total, df2)
