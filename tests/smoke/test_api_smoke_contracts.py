from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.src.api import app

client = TestClient(app)


@pytest.mark.smoke
@pytest.mark.api
def test_system_health_contract():
    with patch("backend.src.core.rpc_manager.RPCManager.get_all_health") as mock_health:
        mock_health.return_value = {
            "primary": {"status": "ok", "latency": 10},
            "secondary": {"status": "ok", "latency": 20},
            "decentralized": {"status": "error", "latency": 0},
        }

        response = client.get("/api/system/health")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"primary", "secondary", "decentralized"}


@pytest.mark.smoke
@pytest.mark.api
def test_system_indicators_contract_with_empty_dataset():
    with patch("backend.src.api.get_data_from_db", return_value=pd.DataFrame()):
        response = client.get("/api/system/indicators")

    assert response.status_code == 200
    assert response.json() == {"rsi": 0, "fear_and_greed": 0, "market_regime": "unknown"}


@pytest.mark.smoke
@pytest.mark.api
def test_get_simulation_status_is_read_only():
    with patch("backend.src.api.run_simulation") as mock_run_simulation:
        with patch("backend.src.api.get_latest_simulation_summary", return_value=None):
            response = client.get("/api/simulation/status")

    assert response.status_code == 200
    mock_run_simulation.assert_not_called()
    payload = response.json()
    assert "running" in payload
    assert "has_results" in payload
    assert "trades_count" in payload


@pytest.mark.smoke
@pytest.mark.api
def test_get_treasuries_summary_is_read_only():
    with patch("backend.src.api.run_trading_system") as mock_run_trading_system:
        with patch("backend.src.api.get_latest_simulation_summary", return_value=None):
            response = client.get("/api/simulation/summary")

    assert response.status_code == 200
    mock_run_trading_system.assert_not_called()
    body = response.json()
    assert set(body.keys()) == {"spot", "defi", "aave", "summary"}


@pytest.mark.smoke
@pytest.mark.api
def test_train_model_endpoint_contract():
    with patch("backend.src.api.train_model_pipeline") as mock_train:
        mock_train.return_value = {
            "success": True,
            "predictions_generated": 12,
            "total_candles": 120,
            "split_date": "2024-01-01",
            "model_type": "XGBClassifier",
        }
        response = client.post("/api/model/train")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "data" in body


@pytest.mark.smoke
@pytest.mark.api
def test_ticker_websocket_contract():
    with client.websocket_connect("/api/ws/ticker") as websocket:
        data = websocket.receive_json()

    assert data["symbol"] == "BTCUSDT"
    assert isinstance(data["price"], float)
    assert "timestamp" in data
