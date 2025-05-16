# logic/depletion.py

import pandas as pd

# 1) Valve‑to‑class mapping
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

# 2) Flow thresholds for Low/Mid/High (Δ in gallons)
FLOW_THRESHOLDS = {
    "Annular":      (3, 7),
    "Pipe Ram":     (5, 10),
    "Shear Ram":    (6, 15),
    "Casing Shear": (8, 18),
    "Connector":    (2, 5),
}

# 3) Per‑stroke depletion weights by valve class
VALVE_DEPLETION_WEIGHTS = {
    "Annular": {
        # Suggested between 0.075/0.225 and 0.5/1.5
        "normal_open":   0.1,   
        "normal_close":  0.5,   
        # Suggested between 0.75 and 3.0
        "high_open":     0.75,    
        "high_close":    0.75,
    },
    "Pipe Ram": {
        # Suggested between 0.05/0.13 and 0.25/0.75
        "normal_open":   0.08,
        "normal_close":  0.45,
        # Suggested between 0.5 and 2.0
        "high_open":     1.25,
        "high_close":    1.25,
    },
    "Connector": {
        # Suggested between 0.5/0.5 and 2.0/2.0
        "normal_open":   1.25,
        "normal_close":  1.25,
        # Suggested between 2.0 and 5.0
        "high_open":     3.5,
        "high_close":    3.5,
    },
    "Shear Ram": {
        # Suggested between 0.025 and 0.10
        "normal_open":   0.05,
        "normal_close":  0.05,
        # Suggested between 0.1 and 0.5
        "high_open":     0.25,
        "high_close":    0.25,
        "shear":         100.0,   # true cut remains full depletion
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
    """Bucket Δ(gal) into Low/Mid/High based on valve class thresholds."""
    low, high = FLOW_THRESHOLDS.get(valve_class, (float("inf"), float("inf")))
    if delta_gal <= low:
        return "Low"
    elif delta_gal <= high:
        return "Mid"
    else:
        return "High"

def estimate_cycle_depletion(valve_class: str, state: str, flow_category: str) -> float:
    """
    Return the depletion % for one OPEN/CLOSE (or SHEAR) stroke.
    For shear‑style valves, actual cuts use 'shear', else picks normal/high + open/close.
    """
    w = VALVE_DEPLETION_WEIGHTS.get(valve_class, {})
    st = state.upper()

    # Actual shear event
    if st == "SHEAR" and "shear" in w:
        return w["shear"]

    # Determine normal vs high
    prefix = "high" if flow_category == "High" else "normal"
    stroke = "open" if st == "OPEN" else "close"
    return w.get(f"{prefix}_{stroke}", 0.0)

def load_and_preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add three new columns:
      • Valve Class
      • Flow Category
      • Depletion (%)
    """
    df = df.copy()
    df["Valve Class"]   = df["valve"].map(VALVE_CLASS_MAP)
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
