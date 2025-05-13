import pandas as pd

def to_ms(dt):
    return int(pd.Timestamp(dt).timestamp() * 1000)

def classify_flow(gal, valve_class, thresholds):
    low_max, mid_max = thresholds.get(valve_class, (5, 10))  # fallback if class missing
    if gal < low_max:
        return "Low"
    elif gal <= mid_max:
        return "Mid"
    else:
        return "High"
