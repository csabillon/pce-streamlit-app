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
):
    st.markdown("### Valve Pressure Cycles – Analysis")

    with st.spinner("Analyzing valve pressure cycles..."):
        cycles_df = analyze_pressure_cycles(df, valve_map, well_pressure_series)

    if cycles_df.empty:
        st.info("No valid pressure cycles found in the selected range.")
        return

    # --- Sidebar controls for thresholds ---
    st.sidebar.markdown("#### Cycle Rarity Threshold")
    RARE_CYCLE_THRESHOLD = st.sidebar.number_input(
        "Highlight cycles above this Well Pressure (psi):",
        min_value=1000, max_value=15000, value=5000, step=500,
        key="rare_cycle_threshold"
    )

    st.sidebar.markdown("#### Wet/Dry Cycle Threshold")
    WET_THRESHOLD = st.sidebar.number_input(
        "Wet/Dry Cycle Threshold (psi):", min_value=0, max_value=2000, value=700, step=10, key="wet_threshold"
    )

    # --- Wet and Dry cycle counts per valve ---
    cycles_df["WetCycle"] = cycles_df["Max Well Pressure"] > WET_THRESHOLD
    wet_counts = cycles_df.groupby("Valve")["WetCycle"].sum().astype(int)
    dry_counts = cycles_df.groupby("Valve")["WetCycle"].apply(lambda x: (~x).sum()).astype(int)
    wet_dry_table = (
        pd.DataFrame({
            "Wet Cycles": wet_counts,
            "Dry Cycles": dry_counts
        })
        .reset_index()
    )

    st.markdown("#### Wet and Dry Cycles per Valve")
    cc1, cc2 = st.columns([2, 3])
    with cc1:
        st.dataframe(
            wet_dry_table,
            use_container_width=True,
            hide_index=True,
            height=min(400, 48 + 35*len(wet_dry_table))
        )
    with cc2:
        fig_wd = go.Figure(data=[
            go.Bar(
                name='Wet', x=wet_dry_table["Valve"], y=wet_dry_table["Wet Cycles"],
                marker_color='royalblue'
            ),
            go.Bar(
                name='Dry', x=wet_dry_table["Valve"], y=wet_dry_table["Dry Cycles"],
                marker_color='lightgray'
            ),
        ])
        fig_wd.update_layout(
            barmode='stack',
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(
                orientation='h',
                yanchor='top', y=0.98,
                xanchor='right', x=0.99,
                font=dict(size=12),
                bgcolor='rgba(0,0,0,0)',
                bordercolor='gray',
                borderwidth=1
            ),
            xaxis_title='Valve',
            yaxis_title='Cycle Count',
            height=300,
        )
        st.plotly_chart(fig_wd, use_container_width=True)

    # --- Time above threshold by valve ---
    def time_above_threshold(cycles_df, threshold):
        df = cycles_df.copy()
        df["HighPressureTime"] = np.where(
            df["Max Well Pressure"] >= threshold,
            df["Duration (min)"],
            0.0
        )
        summary = df.groupby("Valve")["HighPressureTime"].sum().reset_index()
        summary.rename(columns={"HighPressureTime": f"Time > {threshold} psi (min)"}, inplace=True)
        return summary

    summary_df = time_above_threshold(cycles_df, RARE_CYCLE_THRESHOLD)
    st.markdown(f"#### Time Above {RARE_CYCLE_THRESHOLD} psi per Valve")
    cta1, cta2 = st.columns([2, 3])
    with cta1:
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, 48 + 35*len(summary_df))
        )
    with cta2:
        fig2 = px.bar(
            summary_df, x="Valve", y=f"Time > {RARE_CYCLE_THRESHOLD} psi (min)",
            color="Valve"
        )
        fig2.update_layout(
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title='Valve', yaxis_title=f"Time > {RARE_CYCLE_THRESHOLD} psi (min)",
            height=300
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- Rare/extreme cycles ---
    rare_cycles = cycles_df[cycles_df["Max Well Pressure"] >= RARE_CYCLE_THRESHOLD]
    st.markdown(f"#### Cycles with Max Well Pressure ≥ {RARE_CYCLE_THRESHOLD} psi")
    st.dataframe(
        rare_cycles,
        use_container_width=True,
        hide_index=True,
        height=min(300, 48 + 35*len(rare_cycles))
    )
    if not rare_cycles.empty:
        st.info(f"{len(rare_cycles)} cycles exceeded {RARE_CYCLE_THRESHOLD} psi.")

    # --- Scatter: Duration vs Max Well Pressure, color=Rare ---
    st.markdown("#### Duration vs Max Well Pressure (All Cycles)")
    fig = px.scatter(
        cycles_df,
        x="Duration (min)", y="Max Well Pressure",
        color=cycles_df["Max Well Pressure"] >= RARE_CYCLE_THRESHOLD,
        hover_data=["Valve", "Close Time", "Open Time"],
        color_discrete_map={True: "crimson", False: "royalblue"},
        labels={"color": f"≥ {RARE_CYCLE_THRESHOLD} psi"},
        height=320
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8), selector=dict(mode='markers'))
    fig.update_layout(
        legend=dict(
            orientation='h',
            yanchor='bottom', y=1.02,
            xanchor='right', x=0.98,
            font=dict(size=12),
            bgcolor='rgba(0,0,0,0)', 
            bordercolor='gray',
            borderwidth=1
        ),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Top 5 most extreme cycles by Pressure x Duration ---
    st.markdown("#### Top 5 Cycles: Pressure × Duration")
    cycles_df["StressMetric"] = cycles_df["Max Well Pressure"] * cycles_df["Duration (min)"]
    top_extreme = cycles_df.sort_values("StressMetric", ascending=False).head(5)
    st.dataframe(
        top_extreme,
        use_container_width=True,
        hide_index=True,
        height=280
    )

    # --- All cycles table (with stress metric) ---
    st.markdown("#### All Valve Pressure Cycles")
    st.dataframe(
        cycles_df,
        use_container_width=True,
        hide_index=True,
        height=min(700, 48 + 35*len(cycles_df))
    )

    # --- Per-Valve Pressure Cycles for Close Cycles above threshold ---
    if not rare_cycles.empty:
        st.markdown("#### Per-Cycle Pressure Trends for Close Cycles (Above Rarity Threshold)")
        valve_options = sorted(rare_cycles["Valve"].unique())
        selected_valve = st.selectbox(
            "Select Valve for Close Cycle Pressure Traces",
            valve_options,
            key="pressure_cycle_valve"
        )
        valve_cycles = rare_cycles[rare_cycles["Valve"] == selected_valve]
        regulator_pressure_series = pressure_series_by_valve.get(selected_valve)
        
        c1, c2 = st.columns(2)
        # --- Regulator Pressure ---
        with c1:
            st.markdown("##### Regulator Pressure (Rare Close Cycles)")
            if regulator_pressure_series is None or regulator_pressure_series.empty:
                st.warning(f"No regulator pressure data for valve {selected_valve}.")
            else:
                fig = plot_regulator_pressure_cycles(valve_cycles, regulator_pressure_series)
                st.plotly_chart(fig, use_container_width=True)
                reg_table = regulator_pressure_summary_table(valve_cycles, regulator_pressure_series)
                st.markdown("###### Regulator Pressure Table for Rare Cycles")
                st.dataframe(reg_table, use_container_width=True, hide_index=True)
                # Optional: Full trend for the selected valve
                st.markdown("###### Full Regulator Pressure Trend (Selected Valve)")
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=regulator_pressure_series.index,
                    y=regulator_pressure_series.values,
                    mode="lines",
                    name="Regulator Pressure",
                    line=dict(width=2, color="mediumblue"),
                ))
                fig_trend.update_layout(
                    xaxis_title="Timestamp",
                    yaxis_title="Regulator Pressure (psi)",
                    height=250,
                    margin=dict(l=20, r=20, t=30, b=20),
                )
                st.plotly_chart(fig_trend, use_container_width=True)
        # --- Well Pressure ---
        with c2:
            st.markdown("##### Well Pressure (Rare Close Cycles)")
            fig_wp = plot_well_pressure_cycles(valve_cycles, well_pressure_series)
            st.plotly_chart(fig_wp, use_container_width=True)
    else:
        st.info("No rare cycles to display regulator or well pressure data.")
