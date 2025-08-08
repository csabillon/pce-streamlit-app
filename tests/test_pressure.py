import numpy as np
import pandas as pd

from logic.pressure import assign_max_pressure_vectorized


def test_assign_max_pressure_vectorized():
    times = pd.date_range("2020-01-01", periods=11, freq="s")
    pressure_series = pd.Series(np.arange(11, dtype=float), index=times)

    events_df = pd.DataFrame(
        {
            "timestamp": [times[2], times[8]],
            "valve": ["A", "B"],
        }
    )

    valve_class = {"A": "short", "B": "long"}
    category_windows = {"short": 4, "long": 10}

    result = assign_max_pressure_vectorized(
        events_df, pressure_series, valve_class, category_windows
    )

    expected = np.array([1.0, 9.0])
    np.testing.assert_allclose(result, expected)
