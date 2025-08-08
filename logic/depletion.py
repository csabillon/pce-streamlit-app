# logic/depletion.py

import pandas as pd
import numpy as np
from functools import lru_cache
import logging

logger = logging.getLogger("depletion")

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

@lru_cache(maxsize=16)
def get_depletion_weight(valve_class, state, flow_category):
    """Return depletion weight for a valve transition.

    Historically this function assumed ``state`` was always a valid string
    (``"OPEN"``, ``"CLOSE"`` or ``"SHEAR"``).  In practice the dataset can
    contain missing values which are represented as ``None``/``NaN``.  Calling
    ``upper()`` on such values raised an ``AttributeError`` during
    ``load_and_preprocess``.  This bubbled up and prevented the dashboard from
    loading.

    The function now guards against non-string states by coercing the input to
    a string and returning a default depletion of ``0.0`` when the state is not
    recognised.
    """

    w = VALVE_DEPLETION_WEIGHTS.get(valve_class, {})

    # Ensure ``state`` is a string to avoid ``AttributeError`` on ``upper()``
    st = str(state).upper()
    if st == "SHEAR" and "shear" in w:
        return w["shear"]
    if st not in {"OPEN", "CLOSE"}:
        return 0.0
    prefix = "high" if flow_category == "High" else "normal"
    stroke = "open" if st == "OPEN" else "close"
    return w.get(f"{prefix}_{stroke}", 0.0)

def classify_flow_category(delta_gal: float, valve_class: str) -> str:
    low, high = FLOW_THRESHOLDS.get(valve_class, (float("inf"), float("inf")))
    if delta_gal <= low:
        return "Low"
    elif delta_gal <= high:
        return "Mid"
    else:
        return "High"

def estimate_cycle_depletion(valve_class: str, state: str, flow_category: str) -> float:
    return get_depletion_weight(valve_class, state, flow_category)

def load_and_preprocess(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        logger.warning("[DEPLETION] load_and_preprocess: Empty DataFrame")
        return df
    df = df.copy()
    df["Valve Class"] = df["valve"].map(VALVE_CLASS_MAP)
    low = df["Valve Class"].map(lambda v: FLOW_THRESHOLDS.get(v, (float("inf"), float("inf")))[0])
    high = df["Valve Class"].map(lambda v: FLOW_THRESHOLDS.get(v, (float("inf"), float("inf")))[1])
    df["Flow Category"] = pd.Categorical(
        np.select(
            [df["Δ (gal)"] <= low, df["Δ (gal)"] <= high],
            ["Low", "Mid"],
            default="High"
        ),
        categories=["Low", "Mid", "High"],
        ordered=True
    )
    df["Depletion (%)"] = [
        get_depletion_weight(vc, s, fc)
        for vc, s, fc in zip(df["Valve Class"], df["state"], df["Flow Category"])
    ]
    return df
