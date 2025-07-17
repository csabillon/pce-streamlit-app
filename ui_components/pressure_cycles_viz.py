import pandas as pd
import plotly.graph_objects as go

def plot_regulator_pressure_cycles(valve_cycles, regulator_pressure_series):
    """
    Plot regulator pressure traces for all rare close cycles of a selected valve.
    """
    fig = go.Figure()
    for i, row in valve_cycles.iterrows():
        t0 = row["Close Time"]
        t1 = row["Open Time"]
        interval = regulator_pressure_series.loc[t0:t1]
        if interval.empty:
            continue
        times = (pd.to_datetime(interval.index) - pd.to_datetime(t0)).total_seconds() / 60
        label = f"Cycle {i+1} ({t0.strftime('%Y-%m-%d %H:%M')})"
        fig.add_trace(go.Scatter(
            x=times,
            y=interval.values,
            mode="lines+markers",
            name=label,
            line=dict(width=2),
            marker=dict(size=4),
        ))
        fig.add_vline(x=0, line_width=1, line_dash="dot", line_color="gray")
        fig.add_vline(x=times.max(), line_width=1, line_dash="dot", line_color="gray")
    fig.update_layout(
        xaxis_title="Minutes since CLOSE event",
        yaxis_title="Regulator Pressure (psi)",
        title="Regulator Pressure (Rare Close Cycles)",
        margin=dict(l=20, r=20, t=40, b=20),
        height=340,
        legend=dict(
            orientation="h",
            yanchor="top", y=1.08,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
    )
    return fig

def plot_well_pressure_cycles(valve_cycles, well_pressure_series):
    """
    Plot well pressure traces for all rare close cycles of a selected valve.
    """
    fig = go.Figure()
    for i, row in valve_cycles.iterrows():
        t0 = row["Close Time"]
        t1 = row["Open Time"]
        interval = well_pressure_series.loc[t0:t1]
        if interval.empty:
            continue
        times = (pd.to_datetime(interval.index) - pd.to_datetime(t0)).total_seconds() / 60
        label = f"Cycle {i+1} ({t0.strftime('%Y-%m-%d %H:%M')})"
        fig.add_trace(go.Scatter(
            x=times,
            y=interval.values,
            mode="lines+markers",
            name=label,
            line=dict(width=2, dash="dot"),
            marker=dict(size=4),
        ))
        fig.add_vline(x=0, line_width=1, line_dash="dot", line_color="gray")
        fig.add_vline(x=times.max(), line_width=1, line_dash="dot", line_color="gray")
    fig.update_layout(
        xaxis_title="Minutes since CLOSE event",
        yaxis_title="Well Pressure (psi)",
        title="Well Pressure (Rare Close Cycles)",
        margin=dict(l=20, r=20, t=40, b=20),
        height=340,
        legend=dict(
            orientation="h",
            yanchor="top", y=1.08,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
    )
    return fig

def regulator_pressure_summary_table(valve_cycles, regulator_pressure_series):
    """
    Return a DataFrame summarizing min/max/avg regulator pressure for each rare cycle.
    """
    reg_table = []
    for i, row in valve_cycles.iterrows():
        t0 = row["Close Time"]
        t1 = row["Open Time"]
        interval = regulator_pressure_series.loc[t0:t1]
        if interval.empty:
            continue
        reg_table.append({
            "Cycle #": i+1,
            "Close Time": t0,
            "Open Time": t1,
            "Duration (min)": row["Duration (min)"],
            "Min Regulator Pressure": round(interval.min(), 2),
            "Max Regulator Pressure": round(interval.max(), 2),
            "Avg Regulator Pressure": round(interval.mean(), 2),
        })
    if reg_table:
        return pd.DataFrame(reg_table)
    else:
        return pd.DataFrame()  # empty table
