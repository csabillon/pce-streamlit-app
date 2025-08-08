from pathlib import Path
import pandas as pd


def load_analog_map(rig: str) -> pd.DataFrame | None:
    """Load analog channel metadata for a given rig.

    Parameters
    ----------
    rig : str
        Rig identifier used in tag namespaces.

    Returns
    -------
    pandas.DataFrame | None
        DataFrame containing at least a ``Ch`` column with channel numbers and
        an ``Analog Name`` column describing each channel. Returns ``None`` if
        no mapping file exists for the requested rig.
    """

    base_dir = Path(__file__).resolve().parent / "analog_files"
    file_path = base_dir / f"{rig}.csv"

    if not file_path.exists():
        return None

    try:
        return pd.read_csv(file_path)
    except Exception:
        # If the file is malformed, fall back to None so callers can decide
        # how to handle missing metadata.
        return None


def build_tag(rig: str, channel: int) -> str:
    """Return the external id for a given analog channel."""

    if rig == "Drillmax":
        base = f"pi-no:{rig}.BOP.CBM"
    else:
        base = f"pi-no:{rig}.BOP.DCP"
    return f"{base}.ScaledValue{channel}"

