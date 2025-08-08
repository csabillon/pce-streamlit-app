import pathlib
import sys

import numpy as np
import pandas as pd

# Ensure project root on path for direct module imports
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from logic.depletion import get_depletion_weight, load_and_preprocess

def test_get_depletion_weight_handles_missing_state():
    # When state is NaN the function should return 0 instead of raising
    weight = get_depletion_weight('Annular', np.nan, 'Low')
    assert weight == 0.0

def test_load_and_preprocess_handles_missing_state():
    df = pd.DataFrame({
        'valve': ['Upper Annular', 'Upper Annular'],
        'state': ['OPEN', None],
        'Δ (gal)': [5, 7],
    })
    out = load_and_preprocess(df)
    # Missing state should be filled with a depletion of 0
    assert out.loc[out['state'].isna(), 'Depletion (%)'].eq(0.0).all()
