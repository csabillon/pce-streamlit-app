# logic/data_loaders.py

from config import *
from cognite.client import CogniteClient, ClientConfig
from cognite.client.credentials import OAuthClientCredentials
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import time
import logging
from functools import lru_cache, wraps

# --- Set up logging for error handling and API feedback
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data_loaders")

# --- Retry Decorator for API calls
def api_retry(max_attempts=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"[API] {func.__name__} failed (attempt {attempt}): {e}")
                    last_exc = e
                    time.sleep(base_delay * (2 ** (attempt - 1)))
            logger.error(f"[API] {func.__name__} failed after {max_attempts} attempts.")
            raise last_exc
        return wrapper
    return decorator

# --- Caching: Credentials and client are safe to cache as they are static
@lru_cache(maxsize=2)
def get_cognite_client():
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
    return CogniteClient(client_config)

# --- Main API fetchers (use retry)
@api_retry()
def fetch_timeseries_df(external_id, start, end):
    client = get_cognite_client()
    try:
        df = client.time_series.data.retrieve_dataframe(external_id=external_id, start=start, end=end)
        if df.empty:
            logger.warning(f"[DATA] No data returned for {external_id} ({start} - {end})")
        return df
    except Exception as e:
        logger.error(f"Error fetching timeseries {external_id}: {e}")
        raise

def get_volume_df(external_id, start, end):
    df = fetch_timeseries_df(external_id, start, end)
    if df.empty or df.shape[1] == 0:
        logger.warning(f"[VOLUME] No data in get_volume_df for {external_id}")
        return pd.DataFrame(columns=["raw_value", "accumulator"])
    col = df.columns[0]
    df = df.rename(columns={col: "raw_value"})
    df["accumulator"] = df["raw_value"] / 10
    return df

def _fetch_valve(name, ext, smap, fmap, start, end):
    df = fetch_timeseries_df(ext, start, end)
    if df.empty or df.shape[1] == 0:
        logger.warning(f"[VALVE] No data for valve {name}, tag {ext}")
        return pd.DataFrame(columns=["state", "function_state", "valve", "status_code"])
    col = df.columns[0]
    df = df.rename(columns={col: "status_code"})
    df["state"] = df["status_code"].map(smap)
    df["function_state"] = df["status_code"].map(fmap)
    df["valve"] = name
    return df.dropna(subset=["state"])[["state", "function_state", "valve", "status_code"]]

def get_valve_df(valve_map, per_valve_simple_map, per_valve_function_map, start, end, max_workers=6):
    # Parallel fetch, logs errors individually
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_fetch_valve, name, ext, per_valve_simple_map[name], per_valve_function_map[name], start, end)
            for name, ext in valve_map.items()
        ]
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                logger.error(f"[VALVE_DF] Error: {e}")
    return results

def _fetch_pressure(valve, ext, start, end):
    df = fetch_timeseries_df(ext, start, end)
    if df.empty or df.shape[1] == 0:
        logger.warning(f"[PRESSURE] No data for pressure {valve}, tag {ext}")
        return pd.DataFrame(columns=["pressure", "valve"])
    col = df.columns[0]
    df = df.rename(columns={col: "pressure"})
    df["valve"] = valve
    return df[["pressure", "valve"]]

def get_pressure_df(pressure_map, start, end, max_workers=6):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_fetch_pressure, valve, ext, start, end)
            for valve, ext in pressure_map.items()
        ]
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                logger.error(f"[PRESSURE_DF] Error: {e}")
    return results

def get_raw_df(external_id, start, end):
    df = fetch_timeseries_df(external_id, start, end)
    if df.empty or df.shape[1] == 0:
        logger.warning(f"[RAW] No data for {external_id}")
        return pd.DataFrame(columns=["value"])
    col = df.columns[0]
    return df.rename(columns={col: "value"})

