import pandas as pd
import numpy as np

from backend.src import prediction_engine as pe
from defi_data_toolkit.indicators import calculate_sma


def make_dummy_df(n=300):
    # Create a DataFrame with required feature columns filled with synthetic data
    rng = np.random.default_rng(42)
    df = pd.DataFrame()
    df["Close"] = np.linspace(100, 200, n) + rng.normal(0, 1, n)
    # compute SMA_50 and SMA_200 using toolkit
    df["SMA_50"] = calculate_sma(df, column="Close", window=50)
    df["SMA_200"] = calculate_sma(df, column="Close", window=200)
    df["dist_from_sma_50"] = (df["Close"] - df["SMA_50"]) / df["SMA_50"]
    df["dist_from_sma_200"] = (df["Close"] - df["SMA_200"]) / df["SMA_200"]

    # Fill other numeric features required by FEATURES with random numbers
    for col in [
        'RSI', 'FNG_Value', 'Implied_Volatility', 'FundingRate', 'OpenInterest', 'VolumeUSD',
        'MACD', 'MACD_Histogram', 'ATR', 'BB_Position', 'Stoch_K', 'OBV'
    ]:
        df[col] = rng.normal(0, 1, n)

    # target
    df['target_price_fell'] = rng.integers(0, 2, size=n)

    # drop rows missing SMA-based values
    df = df.dropna()
    return df


def test_prediction_engine_uses_dist_from_sma_200():
    # FEATURE list must include the new feature
    assert 'dist_from_sma_200' in pe.FEATURES

    df = make_dummy_df()
    assert 'dist_from_sma_200' in df.columns

    model, scaler = pe.train_prediction_model(df)
    assert model is not None and scaler is not None
