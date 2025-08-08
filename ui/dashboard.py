import streamlit as st
import pandas as pd
import numpy as np

from ui_components.charts import (
    plot_open_close_pie_bar,
    plot_boxplots,
    plot_pressure_boxplots,
    plot_scatter_by_flowcategory,
    plot_time_series,
    plot_accumulator,
)
from ui_components.tables import generate_statistics_table, generate_details_table

def _render_kpi(label: str, value: str):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _inject_kpi_css():
    st.markdown(
        """
        <style>
        .kpi-card{
            color: var(--text-color);
            border:1.5px solid currentColor;
            border-radius:18px;
            padding:12px 16px;
            text-align:center;
            background:transparent;
            transition: box-shadow 120ms ease, transform 120ms ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        }
        .kpi-card:hover{
            box-shadow: 0 4px 14px rgba(0,0,0,0.20);
            transform: translateY(-1px);
        }
        .kpi-label{
            font-size:0.92rem;
            color: currentColor;
            opacity:0.9;
            margin-bottom:2px;
        }
        .kpi-value{
            font-size:1.6rem;
            font-weight:600;
            color: currentColor;
            line-height:1.2;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_dashboard(
    df: pd.DataFrame,
    vol_df: pd.DataFrame,
    plotly_template: str,
    oc_colors: dict,
    flow_colors: dict,
    flow_category_order: list,
    valve_order: list,
    *,
    cycles_df: pd.DataFrame | None = None,
):
    pod_names = ["Composite", "Blue Pod", "Yellow Pod"]
    tabs = st.tabs(pod_names)
    shared_key = "selected_valve"

    for pod_name, tab in zip(pod_names, tabs):
        with tab:
            if pod_name == "Composite":
                st.subheader("Composite – Valve Analytics")
                pod_events = df.copy()
            else:
                st.subheader(f"{pod_name} – Valve Analytics")
                pod_events = df[df["Active Pod"] == pod_name]

            if pod_events.empty:
                st.warning(f"No events for {pod_name}")
                continue

            available = pod_events["valve"].unique()
            valid_valves = [v for v in valve_order if v in available]
            if not valid_valves:
                st.warning("No valid valves for this pod.")
                continue
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

            _inject_kpi_css()

            wet_threshold = int(st.session_state.get("wet_threshold", 700))
            rare_threshold = int(st.session_state.get("rare_cycle_threshold", 2500))

            open_count = int((sub["state"] == "OPEN").sum())
            close_count = int((sub["state"] == "CLOSE").sum())

            mwp = sub["Max Well Pressure"] if "Max Well Pressure" in sub.columns else pd.Series([np.nan] * len(sub), index=sub.index)
            wet_open = int(((sub["state"] == "OPEN") & (mwp > wet_threshold)).sum())
            wet_close = int(((sub["state"] == "CLOSE") & (mwp > wet_threshold)).sum())

            sel_cycles = pd.DataFrame()
            if isinstance(cycles_df, pd.DataFrame) and not cycles_df.empty:
                sel_cycles = cycles_df[cycles_df["Valve"] == choice]

            if not sel_cycles.empty:
                cycles_cnt = int(len(sel_cycles))
                avg_cycle_min = float(sel_cycles["Duration (min)"].mean())
                total_cycle_min = float(sel_cycles["Duration (min)"].sum())
            else:
                cycles_cnt = 0
                avg_cycle_min = 0.0
                total_cycle_min = 0.0

            kcols = st.columns(7)
            with kcols[0]:
                _render_kpi(f"Pressure Cycles ≥ {rare_threshold} psi", f"{cycles_cnt}")
            with kcols[1]:
                _render_kpi("Avg Cycle Duration", f"{avg_cycle_min:.0f} min")
            with kcols[2]:
                _render_kpi("Total Cycle Duration", f"{total_cycle_min:.0f} min")
            with kcols[3]:
                _render_kpi("Open Cycles", f"{open_count}")
            with kcols[4]:
                _render_kpi("Close Cycles", f"{close_count}")
            with kcols[5]:
                _render_kpi(f"Wet Open (>{wet_threshold} psi)", f"{wet_open}")
            with kcols[6]:
                _render_kpi(f"Wet Close (>{wet_threshold} psi)", f"{wet_close}")

            st.subheader("Pressure and Flow Distribution by Flow Category")
            c1, c2, c3, c4 = st.columns(4)
            po, bo, pc, bc = plot_open_close_pie_bar(sub, flow_colors)
            c1.plotly_chart(po, use_container_width=True, key=f"{pod_name}_pie_open")
            c2.plotly_chart(bo, use_container_width=True, key=f"{pod_name}_bar_open")
            c3.plotly_chart(pc, use_container_width=True, key=f"{pod_name}_pie_close")
            c4.plotly_chart(bc, use_container_width=True, key=f"{pod_name}_bar_close")

            b1, b2, b3, b4 = st.columns(4)
            bd_o, bd_c = plot_boxplots(sub, flow_colors, plotly_template)
            bp_o, bp_c = plot_pressure_boxplots(sub, flow_colors, plotly_template)
            b1.plotly_chart(bd_o, use_container_width=True, key=f"{pod_name}_bd_open")
            b2.plotly_chart(bp_o, use_container_width=True, key=f"{pod_name}_bp_open")
            b3.plotly_chart(bd_c, use_container_width=True, key=f"{pod_name}_bd_close")
            b4.plotly_chart(bp_c, use_container_width=True, key=f"{pod_name}_bp_close")

            s1, s2, s3, s4 = st.columns(4)
            scatter_figs = plot_scatter_by_flowcategory(
                sub, flow_colors, flow_category_order, plotly_template
            )
            s1.plotly_chart(scatter_figs[0], use_container_width=True, key=f"{pod_name}_fr_open")
            s2.plotly_chart(scatter_figs[1], use_container_width=True, key=f"{pod_name}_d_open")
            s3.plotly_chart(scatter_figs[2], use_container_width=True, key=f"{pod_name}_fr_close")
            s4.plotly_chart(scatter_figs[3], use_container_width=True, key=f"{pod_name}_d_close")

            st.subheader("Pressure and Flow Over Time")
            ts_fig = plot_time_series(sub, plotly_template, oc_colors)
            st.plotly_chart(ts_fig, use_container_width=True, key=f"{pod_name}_time")

            st.subheader("Accumulator Totalizer")
            fig_acc = plot_accumulator(vol_df, plotly_template)
            st.plotly_chart(fig_acc, use_container_width=True, key=f"{pod_name}_acc")

            st.markdown("---")
            st.subheader("Valve Event Statistics")
            stats_table = generate_statistics_table(pod_events)
            if stats_table.empty:
                st.info("No statistics available for this selection.")
            else:
                st.dataframe(
                    stats_table,
                    use_container_width=True,
                    hide_index=True,
                    key=f"{pod_name}_stats"
                )

            st.subheader("Valve Event Details")
            details_table = generate_details_table(pod_events)
            if details_table.empty:
                st.info("No event details available for this selection.")
            else:
                st.dataframe(
                    details_table,
                    use_container_width=True,
                    hide_index=True,
                    key=f"{pod_name}_details"
                )
