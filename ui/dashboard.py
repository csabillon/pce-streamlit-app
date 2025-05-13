# ui/dashboard.py

import streamlit as st
import pandas as pd

from ui.charts import (
    plot_open_close_pie_bar,
    plot_boxplots,
    plot_pressure_boxplots,
    plot_pressure_vs_flowrate,
    plot_pressure_vs_delta,
    plot_time_series,
    plot_accumulator,
)
from ui.tables import generate_statistics_table, generate_details_table

def render_dashboard(
    df: pd.DataFrame,
    vol_df: pd.DataFrame,
    plotly_template: str,
    grafana_colors: dict,
    flow_colors: dict,
    flow_category_order: list[str],
):
    pod_names = ["Blue Pod", "Yellow Pod"]
    tabs = st.tabs(pod_names)

    for pod_name, tab in zip(pod_names, tabs):
        with tab:
            st.subheader(f"{pod_name} – Valve Analytics")

            pod_events = df[df["Active Pod"] == pod_name]
            if pod_events.empty:
                st.warning(f"No events for {pod_name}")
                continue

            # Valve selector
            choice = st.selectbox(
                "Select Valve",
                pod_events["valve"].unique(),
                key=f"sel_{pod_name}",
            )
            sub = pod_events[pod_events["valve"] == choice].copy()
            sub["Flow Category"] = pd.Categorical(
                sub["Flow Category"],
                categories=flow_category_order,
                ordered=True,
            )

            # ───────────────────────────────────────────────────
            # Row 1: Pie & Bar
            st.subheader("Pressure and Flow Distribution by Flow Category")
            c1, c2, c3, c4 = st.columns(4)
            po, bo, pc, bc = plot_open_close_pie_bar(sub, flow_colors)
            c1.plotly_chart(po, use_container_width=True, key=f"{pod_name}_pie_open")
            c2.plotly_chart(bo, use_container_width=True, key=f"{pod_name}_bar_open")
            c3.plotly_chart(pc, use_container_width=True, key=f"{pod_name}_pie_close")
            c4.plotly_chart(bc, use_container_width=True, key=f"{pod_name}_bar_close")

            # ───────────────────────────────────────────────────
            # Row 2: Boxplots for Δ and for Pressure
            st.markdown("---")
            st.subheader("Boxplots by Flow Category")
            b1, b2, b3, b4 = st.columns(4)
            # Δ (gal) boxplots
            bd_o, bd_c = plot_boxplots(sub, flow_colors, plotly_template)
            # Pressure boxplots
            bp_o, bp_c = plot_pressure_boxplots(sub, flow_colors, plotly_template)
            b1.plotly_chart(bd_o, use_container_width=True, key=f"{pod_name}_bd_open")
            b2.plotly_chart(bp_o, use_container_width=True, key=f"{pod_name}_bp_open")
            b3.plotly_chart(bd_c, use_container_width=True, key=f"{pod_name}_bd_close")
            b4.plotly_chart(bp_c, use_container_width=True, key=f"{pod_name}_bp_close")

            # ───────────────────────────────────────────────────
            # Row 3: Scatter – Pressure vs Flow Rate & vs Δ
            st.markdown("---")
            st.subheader("Pressure vs Flow Rate & Δ Flow")
            s1, s2, s3, s4 = st.columns(4)
            fr_o, fr_c = plot_pressure_vs_flowrate(sub, flow_colors, plotly_template)
            d_o, d_c   = plot_pressure_vs_delta(sub, flow_colors, plotly_template)
            s1.plotly_chart(fr_o, use_container_width=True, key=f"{pod_name}_fr_open")
            s2.plotly_chart(d_o, use_container_width=True, key=f"{pod_name}_d_open")
            s3.plotly_chart(fr_c, use_container_width=True, key=f"{pod_name}_fr_close")
            s4.plotly_chart(d_c, use_container_width=True, key=f"{pod_name}_d_close")

            # ───────────────────────────────────────────────────
            # Time Series
            st.markdown("---")
            st.subheader("Pressure and Flow Over Time")
            ts_fig = plot_time_series(sub, plotly_template, grafana_colors)
            st.plotly_chart(ts_fig, use_container_width=True, key=f"{pod_name}_time")

            # ───────────────────────────────────────────────────
            # Tables
            st.markdown("---")
            st.subheader("Valve Event Statistics")
            st.dataframe(
                generate_statistics_table(pod_events),
                use_container_width=True,
                hide_index=True,
                key=f"{pod_name}_stats"
            )

            st.subheader("Valve Event Details")
            st.dataframe(
                generate_details_table(pod_events),
                use_container_width=True,
                hide_index=True,
                key=f"{pod_name}_details"
            )

            # ───────────────────────────────────────────────────
            # Accumulator (global both pods)
            st.markdown("---")
            st.subheader("Accumulator Totalizer (Gallons Over Time)")
            fig_acc = plot_accumulator(vol_df, plotly_template)
            st.plotly_chart(
                fig_acc,
                use_container_width=True,
                key=f"{pod_name}_acc"
            )
