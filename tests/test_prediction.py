import pytest
import pandas as pd
import numpy as np
from backend.src.ai.prediction import train_prediction_model, get_predictions, FEATURES, TARGET

@pytest.fixture
def dummy_data():
    # Create dummy data with 100 rows
    np.random.seed(42)
    data = {
        'Open_time': pd.date_range(start='2023-01-01', periods=100, freq='4h'),
        'RSI': np.random.uniform(20, 80, 100),
        'dist_from_ema_50': np.random.uniform(-1000, 1000, 100),
        'dist_from_sma_200': np.random.uniform(-1000, 1000, 100),
        'BB_Width': np.random.uniform(0.01, 0.1, 100),
        'FundingRate': np.random.uniform(-0.01, 0.01, 100),
        'OpenInterest': np.random.uniform(1e8, 1e9, 100),
        'VolumeUSD': np.random.uniform(1e6, 1e7, 100),
        'oi_change_4h': np.random.uniform(-0.05, 0.05, 100),
        'funding_velocity': np.random.uniform(-0.0001, 0.0001, 100),
        TARGET: np.random.randint(0, 2, 100)
    }
    return pd.DataFrame(data)

def test_train_prediction_model(dummy_data):
    # Split date in the middle
    split_date = '2023-01-08'
    model, scaler = train_prediction_model(dummy_data, train_test_split_date=split_date)
    
    assert model is not None
    assert scaler is not None
    # Check if features are usable
    assert len(model.feature_importances_) == len(FEATURES)

def test_get_predictions(dummy_data):
    model, scaler = train_prediction_model(dummy_data, train_test_split_date='2023-01-08')
    
    # Get predictions for the same data
    df_pred = get_predictions(model, scaler, dummy_data)
    
    assert 'prediction' in df_pred.columns
    assert 'prediction_proba' in df_pred.columns
    assert 'prediction_correct' in df_pred.columns
    assert df_pred['prediction_proba'].between(0, 1).all()

def test_train_prediction_model_no_target():
    df = pd.DataFrame({'Open_time': [pd.Timestamp('2023-01-01')]})
    model, scaler = train_prediction_model(df)
    assert model is None
    assert scaler is None
