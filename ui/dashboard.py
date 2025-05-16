# ui/dashboard.py

import streamlit as st
import pandas as pd

from ui.charts import (
    plot_open_close_pie_bar,
    plot_boxplots,
    plot_pressure_boxplots,
    plot_scatter_by_flowcategory,
    plot_time_series,
    plot_accumulator,
)
from ui.tables import generate_statistics_table, generate_details_table

def render_dashboard(
    df: pd.DataFrame,
    vol_df: pd.DataFrame,
    plotly_template: str,
    oc_colors: dict,
    flow_colors: dict,
    flow_category_order: list[str],
    valve_order: list[str],
):
    pod_names = ["Blue Pod", "Yellow Pod"]
    tabs = st.tabs(pod_names)
    shared_key = "selected_valve"

    for pod_name, tab in zip(pod_names, tabs):
        with tab:
            st.subheader(f"{pod_name} – Valve Analytics")

            pod_events = df[df["Active Pod"] == pod_name]
            if pod_events.empty:
                st.warning(f"No events for {pod_name}")
                continue

            # Select Valve
            available    = pod_events["valve"].unique()
            valid_valves = [v for v in valve_order if v in available]
            default_valve = st.session_state.get(shared_key, valid_valves[0])
            if default_valve not in valid_valves:
                default_valve = valid_valves[0]
            default_index = valid_valves.index(default_valve)

            choice = st.selectbox(
                "Select Valve",
                valid_valves,
                index=default_index,
                key=f"sel_{pod_name}",
            )
            st.session_state[shared_key] = choice

            sub = pod_events[pod_events["valve"] == choice].copy()
            sub["Flow Category"] = pd.Categorical(
                sub["Flow Category"],
                categories=flow_category_order,
                ordered=True,
            )

            # Row 1: Pie & Bar
            st.subheader("Pressure and Flow Distribution by Flow Category")
            c1, c2, c3, c4 = st.columns(4)
            po, bo, pc, bc = plot_open_close_pie_bar(sub, flow_colors)
            c1.plotly_chart(po, use_container_width=True, key=f"{pod_name}_pie_open")
            c2.plotly_chart(bo, use_container_width=True, key=f"{pod_name}_bar_open")
            c3.plotly_chart(pc, use_container_width=True, key=f"{pod_name}_pie_close")
            c4.plotly_chart(bc, use_container_width=True, key=f"{pod_name}_bar_close")

            # Row 2: Boxplots
            st.markdown("---")
            b1, b2, b3, b4 = st.columns(4)
            bd_o, bd_c = plot_boxplots(sub, flow_colors, plotly_template)
            bp_o, bp_c = plot_pressure_boxplots(sub, flow_colors, plotly_template)
            b1.plotly_chart(bd_o, use_container_width=True, key=f"{pod_name}_bd_open")
            b2.plotly_chart(bp_o, use_container_width=True, key=f"{pod_name}_bp_open")
            b3.plotly_chart(bd_c, use_container_width=True, key=f"{pod_name}_bd_close")
            b4.plotly_chart(bp_c, use_container_width=True, key=f"{pod_name}_bp_close")

            # Row 3: Scatter by Flow Category
            st.markdown("---")
            s1, s2, s3, s4 = st.columns(4)
            scatter_figs = plot_scatter_by_flowcategory(
                sub, flow_colors, flow_category_order, plotly_template
            )
            s1.plotly_chart(scatter_figs[0], use_container_width=True, key=f"{pod_name}_fr_open")
            s2.plotly_chart(scatter_figs[1], use_container_width=True, key=f"{pod_name}_d_open")
            s3.plotly_chart(scatter_figs[2], use_container_width=True, key=f"{pod_name}_fr_close")
            s4.plotly_chart(scatter_figs[3], use_container_width=True, key=f"{pod_name}_d_close")

            # Time Series
            st.markdown("---")
            st.subheader("Pressure and Flow Over Time")
            ts_fig = plot_time_series(sub, plotly_template, oc_colors)
            st.plotly_chart(ts_fig, use_container_width=True, key=f"{pod_name}_time")

            # Accumulator
            st.markdown("---")
            st.subheader("Accumulator Totalizer")
            fig_acc = plot_accumulator(vol_df, plotly_template)
            st.plotly_chart(fig_acc, use_container_width=True, key=f"{pod_name}_acc")

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
