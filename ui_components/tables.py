# ui_components/tables.py

import pandas as pd

def generate_statistics_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    agg_dict_full = {
        "Count":                    ("Δ (gal)",             "count"),
        "Avg Δ (gal)":              ("Δ (gal)",             "mean"),
        "Min Δ (gal)":              ("Δ (gal)",             "min"),
        "Max Δ (gal)":              ("Δ (gal)",             "max"),
        "Total Volume (gal)":       ("Δ (gal)",             "sum"),
        "Avg Reg Pressure (psi)":   ("Max Pressure",        "mean"),
        "Min Reg Pressure (psi)":   ("Max Pressure",        "min"),
        "Max Reg Pressure (psi)":   ("Max Pressure",        "max"),
        "Avg Well Pressure (psi)":  ("Max Well Pressure",   "mean"),
        "Min Well Pressure (psi)":  ("Max Well Pressure",   "min"),
        "Max Well Pressure (psi)":  ("Max Well Pressure",   "max"),
        "Avg Flow (gpm)":           ("Flow Rate (gpm)",     "mean"),
        "Total Depletion (%)":      ("Depletion (%)",       "sum"),
        "Most Recent Status Code":  ("status_code",         "last"),
    }
    agg_dict = {
        k: v for k, v in agg_dict_full.items()
        if v[0] in df.columns
    }
    result = (
        df
        .groupby(["valve", "state", "Active Pod"])
        .agg(**agg_dict)
        .round(2)
        .reset_index()
    )
    return result

def generate_details_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = [
        "timestamp",
        "valve",
        "prev_state",
        "state",
        "function_state",
        "display_state",
        "status_code",
        "Start Time",
        "End Time",
        "Start (gal)",
        "End (gal)",
        "Δ (gal)",
        "Duration (min)",
        "Flow Rate (gpm)",
        "Max Reg Pressure",
        "Max Well Pressure",
        "Active Pod",
        "Flow Category",
        "Depletion (%)",
    ]
    existing = [c for c in cols if c in df.columns]
    return df[existing]
