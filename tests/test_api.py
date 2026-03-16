import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.src.api import app

client = TestClient(app)

def test_api_history_mocked():
    with patch('backend.src.data.storage.create_connection') as mock_conn:
        mock_conn.return_value = MagicMock()
        # Mock pd.read_sql
        with patch('pandas.read_sql') as mock_read_sql:
            mock_read_sql.return_value = pd.DataFrame([
                {'time': 1700000000000, 'open': 60000, 'high': 61000, 'low': 59000, 'close': 60500, 'volume': 100}
            ])
            response = client.get("/api/history")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['close'] == 60500

def test_api_simulation_status():
    with patch('backend.src.api.get_latest_simulation_summary') as mock_summary:
        mock_summary.return_value = {'total_trades': 10}
        response = client.get("/api/simulation/status")
        assert response.status_code == 200
        assert response.json()['trades_count'] == 10

@patch('backend.src.api.train_model_pipeline')
def test_api_model_train(mock_train):
    mock_train.return_value = {
        "success": True,
        "predictions_generated": 100,
        "total_candles": 1000,
        "split_date": "2024-01-01",
        "model_type": "XGBClassifier"
    }
    response = client.post("/api/model/train")
    assert response.status_code == 200
    assert "Modelo treinado com sucesso" in response.json()['message']

@patch('backend.src.api.get_predictions_from_db')
@patch('backend.src.api.run_simulation')
def test_api_simulation_run(mock_run, mock_preds):
    # Mock pre-existing predictions
    mock_preds.return_value = pd.DataFrame([{'dummy': 1}])
    
    payload = {
        "initial_capital": 1000.0,
        "simulation_days": 30,
        "strategy_type": "accumulator"
    }
    response = client.post("/api/simulation/run", json=payload)
    assert response.status_code == 200
    assert "Simulação iniciada" in response.json()['message']

def test_api_simulation_run_no_model(mock_preds=None):
    with patch('backend.src.api.get_predictions_from_db') as mock_preds:
        mock_preds.return_value = None # No model trained
        
        payload = {"initial_capital": 1000.0}
        response = client.post("/api/simulation/run", json=payload)
        assert response.status_code == 400
        assert "Modelo não treinado" in response.json()['detail']
