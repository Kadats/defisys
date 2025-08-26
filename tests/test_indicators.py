import pandas as pd
import numpy as np
from backend.src.indicators import calculate_sma, calculate_atr


def make_sample_df():
    dates = pd.date_range('2023-01-01', periods=30, freq='D')
    close = np.linspace(100, 130, 30)
    high = close + np.random.rand(30) * 2
    low = close - np.random.rand(30) * 2
    df = pd.DataFrame({'Open_time': dates, 'Close': close, 'High': high, 'Low': low})
    return df


def test_sma_basic():
    df = make_sample_df()
    sma = calculate_sma(df, column='Close', window=5)
    assert len(sma) == len(df)
    assert not sma.isnull().all()


def test_atr_basic():
    df = make_sample_df()
    atr = calculate_atr(df, high_col='High', low_col='Low', close_col='Close', window=14)
    assert len(atr) == len(df)
    assert not atr.isnull().all()
