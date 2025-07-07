# ui/tables.py
import pandas as pd

def generate_statistics_table(df: pd.DataFrame) -> pd.DataFrame:
    agg_dict = {
        "Count":                    ("Δ (gal)",             "count"),
        "Avg Δ (gal)":              ("Δ (gal)",             "mean"),
        "Min Δ (gal)":              ("Δ (gal)",             "min"),
        "Max Δ (gal)":              ("Δ (gal)",             "max"),
        "Total Volume (gal)":       ("Δ (gal)",             "sum"),
        "Avg Pressure (psi)":       ("Max Pressure",        "mean"),
        "Min Pressure (psi)":       ("Max Pressure",        "min"),
        "Max Pressure (psi)":       ("Max Pressure",        "max"),
        "Avg Well Pressure (psi)":  ("Max Well Pressure",   "mean"),
        "Min Well Pressure (psi)":  ("Max Well Pressure",   "min"),
        "Max Well Pressure (psi)":  ("Max Well Pressure",   "max"),
        "Avg Flow (gpm)":           ("Flow Rate (gpm)",     "mean"),
        "Total Depletion (%)":      ("Depletion (%)",       "sum"),
    }
    return (
        df
        .groupby(["valve", "state", "Active Pod"])
        .agg(**agg_dict)
        .round(2)
        .reset_index()
    )

def generate_details_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "timestamp",
        "valve",
        "prev_state",
        "state",
        "Start Time",
        "End Time",
        "Start (gal)",
        "End (gal)",
        "Δ (gal)",
        "Duration (min)",
        "Flow Rate (gpm)",
        "Max Pressure",
        "Max Well Pressure",
        "Active Pod",
        "Flow Category",
        "Depletion (%)",
    ]
    return df[cols]
