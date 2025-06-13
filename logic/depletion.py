# logic/depletion.py

import pandas as pd

VALVE_CLASS_MAP = {
    "Upper Annular":      "Annular",
    "Lower Annular":      "Annular",
    "Upper Pipe Ram":     "Pipe Ram",
    "Middle Pipe Ram":    "Pipe Ram",
    "Lower Pipe Ram":     "Pipe Ram",
    "Test Ram":           "Pipe Ram",
    "Upper Blind Shear":  "Shear Ram",
    "Lower Blind Shear":  "Shear Ram",
    "Casing Shear Ram":   "Casing Shear",
    "LMRP Connector":     "Connector",
    "Wellhead Connector": "Connector",
}

FLOW_THRESHOLDS = {
    "Annular":      (3, 7),
    "Pipe Ram":     (5, 10),
    "Shear Ram":    (6, 15),
    "Casing Shear": (8, 18),
    "Connector":    (2, 5),
}

VALVE_DEPLETION_WEIGHTS = {
    "Annular": {
        "normal_open":   0.1,   
        "normal_close":  0.5,   
        "high_open":     0.75,    
        "high_close":    0.75,
    },
    "Pipe Ram": {
        "normal_open":   0.08,
        "normal_close":  0.45,
        "high_open":     1.25,
        "high_close":    1.25,
    },
    "Connector": {
        "normal_open":   1.25,
        "normal_close":  1.25,
        "high_open":     3.5,
        "high_close":    3.5,
    },
    "Shear Ram": {
        "normal_open":   0.05,
        "normal_close":  0.05,
        "high_open":     0.25,
        "high_close":    0.25,
        "shear":         100.0,
    },
    "Casing Shear": {
        "normal_open":   0.05,
        "normal_close":  0.05,
        "high_open":     0.25,
        "high_close":    0.25,
        "shear":         100.0,
    },
}

def classify_flow_category(delta_gal: float, valve_class: str) -> str:
    low, high = FLOW_THRESHOLDS.get(valve_class, (float("inf"), float("inf")))
    if delta_gal <= low:
        return "Low"
    elif delta_gal <= high:
        return "Mid"
    else:
        return "High"

def estimate_cycle_depletion(valve_class: str, state: str, flow_category: str) -> float:
    w = VALVE_DEPLETION_WEIGHTS.get(valve_class, {})
    st = state.upper()
    if st == "SHEAR" and "shear" in w:
        return w["shear"]
    prefix = "high" if flow_category == "High" else "normal"
    stroke = "open" if st == "OPEN" else "close"
    return w.get(f"{prefix}_{stroke}", 0.0)

def load_and_preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Valve Class"] = df["valve"].map(VALVE_CLASS_MAP)
    df["Flow Category"] = df.apply(
        lambda r: classify_flow_category(r["Δ (gal)"], r["Valve Class"]), axis=1
    )
    df["Depletion (%)"] = df.apply(
        lambda r: estimate_cycle_depletion(
            valve_class   = r["Valve Class"],
            state         = r["state"],
            flow_category = r["Flow Category"],
        ),
        axis=1,
    )
    return df
