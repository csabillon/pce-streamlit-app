from config import *
from cognite.client import CogniteClient

client = CogniteClient.default_oauth_client_credentials(
    CDF_PROJECT, CDF_CLUSTER, CDF_TENANT_ID, CDF_CLIENT_ID, CDF_CLIENT_SECRET
)

def get_volume_df(external_id, start, end):
    """Accumulator series: raw_value comes in tenths of gallons => divide by 10."""
    df = client.time_series.data.retrieve_dataframe(external_id=external_id,
                                                   start=start, end=end)
    df = df.rename(columns={df.columns[0]: "raw_value"})
    df["accumulator"] = df["raw_value"] / 10
    return df

def get_valve_df(valve_map, simple_map, start, end):
    dfs = []
    for name, ext in valve_map.items():
        df = client.time_series.data.retrieve_dataframe(external_id=ext,
                                                       start=start, end=end)
        df = df.rename(columns={df.columns[0]: "status_code"})
        df["state"] = df["status_code"].map(simple_map)
        df["valve"] = name
        dfs.append(df.dropna(subset=["state"])[["state", "valve"]])
    return dfs

def get_pressure_df(pressure_map, start, end):
    dfs = []
    for valve, ext in pressure_map.items():
        df = client.time_series.data.retrieve_dataframe(external_id=ext,
                                                       start=start, end=end)
        df = df.rename(columns={df.columns[0]: "pressure"})
        df["valve"] = valve
        dfs.append(df[["pressure", "valve"]])
    return dfs

def get_raw_df(external_id, start, end):
    """Generic raw signal (no divide)."""
    df = client.time_series.data.retrieve_dataframe(external_id=external_id,
                                                   start=start, end=end)
    # rename the single column to 'value'
    return df.rename(columns={df.columns[0]: "value"})
