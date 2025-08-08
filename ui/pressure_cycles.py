# ui/pressure_cycles.py

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from logic.pressure_cycles import analyze_pressure_cycles
from ui_components.pressure_cycles_viz import (
    plot_regulator_pressure_cycles, 
    plot_well_pressure_cycles,
    regulator_pressure_summary_table
)

def render_pressure_cycles(
    df,          
    valve_map, 
    well_pressure_series,
    pressure_series_by_valve,   # Dict[str, pd.Series]
    cycles_df=None,             # may already be filtered by Rare threshold
):
    st.markdown("### Valve Pressure Cycles – Analysis")

    with st.spinner("Analyzing valve pressure cycles..."):
        if isinstance(cycles_df, pd.DataFrame) and not cycles_df.empty:
            local_cycles = cycles_df.copy()
        else:
            wps = well_pressure_series.copy()
            wps.index = pd.to_datetime(wps.index)
            wps = wps.sort_index()
            local_cycles = analyze_pressure_cycles(df, valve_map, wps)

    if local_cycles.empty:
        st.info("No valid pressure cycles found in the selected range.")
        return

    RARE_CYCLE_THRESHOLD = int(st.session_state.get("rare_cycle_threshold", 5000))
    WET_THRESHOLD = int(st.session_state.get("wet_threshold", 700))

    local_cycles = local_cycles.copy()
    local_cycles["WetCycle"] = local_cycles["Max Well Pressure"] > WET_THRESHOLD

    wet_counts = local_cycles.groupby("Valve")["WetCycle"].sum().astype(int)
    dry_counts = local_cycles.groupby("Valve")["WetCycle"].apply(lambda x: (~x).sum()).astype(int)
    wet_dry_table = pd.DataFrame({"Valve": wet_counts.index, "Wet Cycles": wet_counts.values, "Dry Cycles": dry_counts.values})

    st.markdown("#### Wet and Dry Cycles per Valve")
    cc1, cc2 = st.columns([2, 3])
    with cc1:
        st.dataframe(wet_dry_table, use_container_width=True, hide_index=True, height=min(400, 48 + 35*len(wet_dry_table)))
    with cc2:
        fig_wd = go.Figure(data=[
            go.Bar(name='Wet', x=wet_dry_table["Valve"], y=wet_dry_table["Wet Cycles"]),
            go.Bar(name='Dry', x=wet_dry_table["Valve"], y=wet_dry_table["Dry Cycles"]),
        ])
        fig_wd.update_layout(
            barmode='stack',
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation='h', yanchor='top', y=0.98, xanchor='right', x=0.99),
            xaxis_title='Valve', yaxis_title='Cycle Count', height=300,
        )
        st.plotly_chart(fig_wd, use_container_width=True)

    def time_above_threshold(cycles_df_in, threshold):
        df_ = cycles_df_in.copy()
        df_["HighPressureTime"] = np.where(df_["Max Well Pressure"] >= threshold, df_["Duration (min)"], 0.0)
        summary = df_.groupby("Valve")["HighPressureTime"].sum().reset_index()
        summary.rename(columns={"HighPressureTime": f"Time > {threshold} psi (min)"}, inplace=True)
        return summary

    summary_df = time_above_threshold(local_cycles, RARE_CYCLE_THRESHOLD)
    st.markdown(f"#### Time Above {RARE_CYCLE_THRESHOLD} psi per Valve")
    cta1, cta2 = st.columns([2, 3])
    with cta1:
        st.dataframe(summary_df, use_container_width=True, hide_index=True, height=min(400, 48 + 35*len(summary_df)))
    with cta2:
        fig2 = px.bar(summary_df, x="Valve", y=f"Time > {RARE_CYCLE_THRESHOLD} psi (min)", color="Valve")
        fig2.update_layout(showlegend=False, margin=dict(l=20, r=20, t=20, b=20), xaxis_title='Valve', yaxis_title=f"Time > {RARE_CYCLE_THRESHOLD} psi (min)", height=300)
        st.plotly_chart(fig2, use_container_width=True)

    rare_cycles = local_cycles[local_cycles["Max Well Pressure"] >= RARE_CYCLE_THRESHOLD]
    st.markdown(f"#### Cycles with Max Well Pressure ≥ {RARE_CYCLE_THRESHOLD} psi")
    st.dataframe(rare_cycles, use_container_width=True, hide_index=True, height=min(300, 48 + 35*len(rare_cycles)))
    if not rare_cycles.empty:
        st.info(f"{len(rare_cycles)} cycles exceeded {RARE_CYCLE_THRESHOLD} psi.")

    st.markdown("#### Duration vs Max Well Pressure (All Cycles)")
    fig = px.scatter(
        local_cycles,
        x="Duration (min)", y="Max Well Pressure",
        color=local_cycles["Max Well Pressure"] >= RARE_CYCLE_THRESHOLD,
        hover_data=["Valve", "Close Time", "Open Time"],
        color_discrete_map={True: "crimson", False: "royalblue"},
        labels={"color": f"≥ {RARE_CYCLE_THRESHOLD} psi"},
        height=320
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8), selector=dict(mode='markers'))
    fig.update_layout(legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=0.98), margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Top 5 Cycles: Pressure × Duration")
    local_cycles["StressMetric"] = local_cycles["Max Well Pressure"] * local_cycles["Duration (min)"]
    top_extreme = local_cycles.sort_values("StressMetric", ascending=False).head(5)
    st.dataframe(top_extreme, use_container_width=True, hide_index=True, height=280)

    st.markdown("#### All Valve Pressure Cycles")
    st.dataframe(local_cycles, use_container_width=True, hide_index=True, height=min(700, 48 + 35*len(local_cycles)))

    if not rare_cycles.empty:
        st.markdown("#### Per-Cycle Pressure Trends for Close Cycles (Above Rare Threshold)")
        valve_options = sorted(rare_cycles["Valve"].unique())
        selected_valve = st.selectbox("Select Valve for Close Cycle Pressure Traces", valve_options, key="pressure_cycle_valve")
        valve_cycles = rare_cycles[rare_cycles["Valve"] == selected_valve]
        regulator_pressure_series = pressure_series_by_valve.get(selected_valve)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Regulator Pressure (Rare Close Cycles)")
            if regulator_pressure_series is None or getattr(regulator_pressure_series, "empty", True):
                st.warning(f"No regulator pressure data for valve {selected_valve}.")
            else:
                from ui_components.pressure_cycles_viz import plot_regulator_pressure_cycles, regulator_pressure_summary_table
                fig = plot_regulator_pressure_cycles(valve_cycles, regulator_pressure_series)
                st.plotly_chart(fig, use_container_width=True)
                reg_table = regulator_pressure_summary_table(valve_cycles, regulator_pressure_series)
                st.markdown("###### Regulator Pressure Table for Rare Cycles")
                st.dataframe(reg_table, use_container_width=True, hide_index=True)
                st.markdown("###### Full Regulator Pressure Trend (Selected Valve)")
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(x=regulator_pressure_series.index, y=regulator_pressure_series.values, mode="lines", name="Regulator Pressure", line=dict(width=2)))
                fig_trend.update_layout(xaxis_title="Timestamp", yaxis_title="Regulator Pressure (psi)", height=250, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_trend, use_container_width=True)
        with c2:
            st.markdown("##### Well Pressure (Rare Close Cycles)")
            from ui_components.pressure_cycles_viz import plot_well_pressure_cycles
            fig_wp = plot_well_pressure_cycles(valve_cycles, well_pressure_series)
            st.plotly_chart(fig_wp, use_container_width=True)
    else:
        st.info("No rare cycles to display regulator or well pressure data.")
