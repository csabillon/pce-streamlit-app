import pandas as pd

def generate_statistics_table(df):
    stats = (
        df.groupby(["valve", "state", "Active Pod"])
          .agg(
              Count=("Δ (gal)", "count"),
              **{
                  "Avg Δ (gal)":   ("Δ (gal)", "mean"),
                  "Min Δ (gal)":   ("Δ (gal)", "min"),
                  "Max Δ (gal)":   ("Δ (gal)", "max"),
                  "Total Volume (gal)": ("Δ (gal)", "sum"),
                  "Avg Pressure (psi)": ("Max Pressure (±30s)", "mean"),
                  "Min Pressure (psi)": ("Max Pressure (±30s)", "min"),
                  "Max Pressure (psi)": ("Max Pressure (±30s)", "max"),
                  "Avg Flow (gpm)":     ("Flow Rate (gpm)", "mean"),
              }
          )
          .round(2)
          .reset_index()
    )
    return stats

def generate_details_table(df):
    return df[
        [
            "timestamp",
            "valve",
            "prev_state",
            "state",
            "Start Time",
            "End Time",
            "Start (gal)",
            "End (gal)",
            "Δ (gal)",
            "Event Duration (min)",
            "Flow Rate (gpm)",
            "Max Pressure (±30s)",
            "Active Pod",
        ]
    ]
