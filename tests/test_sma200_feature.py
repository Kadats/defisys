import pandas as pd
import numpy as np

from backend.src.ai import prediction as pe
from backend.src.utils.indicators import calculate_sma


def make_dummy_df(n=3000):
    # Create a DataFrame with required feature columns filled with synthetic data
    # Use 3000 samples to ensure we have data both before and after 2022-01-01 split
    # 3000 samples * 4h = 12000h = 500 days, spanning from 2021-01-01 to mid-2022
    rng = np.random.default_rng(42)
    df = pd.DataFrame()
    df["Open_time"] = pd.date_range(start='2021-01-01', periods=n, freq='4h')
    df["Close"] = np.linspace(100, 200, n) + rng.normal(0, 1, n)
    # Indicators
    df["SMA_50"] = calculate_sma(df, column="Close", window=50)
    df["SMA_200"] = calculate_sma(df, column="Close", window=200)
    df["dist_from_ema_50"] = (df["Close"] - df["SMA_50"]) / df["SMA_50"]
    df["dist_from_sma_200"] = (df["Close"] - df["SMA_200"]) / df["SMA_200"]
    df["BB_Width"] = 0.05

    # Fill other numeric features required by FEATURES with random numbers
    for col in [
        'RSI', 'FundingRate', 'OpenInterest', 'VolumeUSD', 'oi_change_4h', 'funding_velocity'
    ]:
        df[col] = rng.normal(0, 1, n)

    # target
    df['Target_Trend'] = rng.integers(0, 2, size=n)

    # drop rows missing SMA-based values
    df = df.dropna()
    return df


def test_prediction_engine_uses_dist_from_sma_200():
    # FEATURE list must include the new feature
    assert 'dist_from_sma_200' in pe.FEATURES

    df = make_dummy_df()
    assert 'dist_from_sma_200' in df.columns

    # Use a split date that falls within our dummy data range
    model, scaler = pe.train_prediction_model(df, train_test_split_date='2021-06-01')
    assert model is not None and scaler is not None
