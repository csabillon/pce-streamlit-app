# logic/data_loaders.py

from config import *
from cognite.client import CogniteClient, ClientConfig
from cognite.client.credentials import OAuthClientCredentials
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

creds = OAuthClientCredentials(
    token_url=AUTHORITY_HOST_URI,
    client_id=CDF_CLIENT_ID,
    client_secret=CDF_CLIENT_SECRET,
    scopes=SCOPES
)

client_config = ClientConfig(
    client_name="client",
    project=CDF_PROJECT,
    credentials=creds,
    base_url=BASE_URL
)

client = CogniteClient(client_config)

# ---- Volume Fetch (unchanged) ----
def get_volume_df(external_id, start, end):
    """Accumulator series: raw_value comes in tenths of gallons => divide by 10."""
    df = client.time_series.data.retrieve_dataframe(external_id=external_id, start=start, end=end)
    df = df.rename(columns={df.columns[0]: "raw_value"})
    df["accumulator"] = df["raw_value"] / 10
    return df

# ---- Parallel Valve Fetch ----
def _fetch_valve(name, ext, simple_map, function_map, start, end):
    df = client.time_series.data.retrieve_dataframe(external_id=ext, start=start, end=end)
    df = df.rename(columns={df.columns[0]: "status_code"})
    df["state"] = df["status_code"].map(simple_map)
    df["function_state"] = df["status_code"].map(function_map)
    df["valve"] = name
    # Drop rows without valid state for transitions, but keep function_state for all
    return df.dropna(subset=["state"])[["state", "function_state", "valve", "status_code"]]

def get_valve_df(valve_map, simple_map, function_map, start, end, max_workers=6):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_fetch_valve, name, ext, simple_map, function_map, start, end)
            for name, ext in valve_map.items()
        ]
        results = [f.result() for f in futures]
    return results

# ---- Parallel Pressure Fetch ----
def _fetch_pressure(valve, ext, start, end):
    df = client.time_series.data.retrieve_dataframe(external_id=ext, start=start, end=end)
    df = df.rename(columns={df.columns[0]: "pressure"})
    df["valve"] = valve
    return df[["pressure", "valve"]]

def get_pressure_df(pressure_map, start, end, max_workers=6):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_fetch_pressure, valve, ext, start, end)
            for valve, ext in pressure_map.items()
        ]
        results = [f.result() for f in futures]
    return results

# ---- Generic Raw Fetch (unchanged) ----
def get_raw_df(external_id, start, end):
    """Generic raw signal (no divide)."""
    df = client.time_series.data.retrieve_dataframe(external_id=external_id, start=start, end=end)
    return df.rename(columns={df.columns[0]: "value"})
