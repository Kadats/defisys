import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.src.api import app

client = TestClient(app)

def test_get_system_health():
    """Testa se o endpoint de saúde do sistema (RPCs) está funcional."""
    with patch('backend.src.core.rpc_manager.RPCManager.get_all_health') as mock_health:
        mock_health.return_value = {
            "primary": {"status": "ok", "latency": 15},
            "secondary": {"status": "ok", "latency": 45},
            "decentralized": {"status": "error", "latency": 0}
        }
        response = client.get("/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert "primary" in data
        assert data["primary"]["status"] == "ok"

def test_get_system_indicators():
    """Testa o retorno de indicadores críticos (RSI, Fear & Greed)."""
    with patch('backend.src.api.get_data_from_db') as mock_db:
        mock_db.return_value = pd.DataFrame([{'dummy': 1}]) # Not empty
        with patch('backend.src.api.heuristics.get_market_indicators') as mock_indicators:
            mock_indicators.return_value = {
                "rsi": 45.5,
                "fear_and_greed": 55,
                "market_regime": "uncertain"
            }
            response = client.get("/api/system/indicators")
            assert response.status_code == 200
            assert response.json()["rsi"] == 45.5

def test_sandbox_run_simulation():
    """Testa se o Sandbox Lab consegue disparar uma simulação isolada."""
    payload = {
        "ai_confidence": 0.8,
        "initial_capital": 5000,
        "train_window": 90,
        "test_window": 30
    }
    with patch('backend.src.api.run_sandbox_simulation') as mock_run:
        mock_run.return_value = {
            "success": True, 
            "job_id": "test-123",
            "metrics": {"roi_total": 12.5, "max_drawdown": 5.2, "win_rate": 65.0},
            "equity_curve": [{"date": "2024-01-01", "equity": 5000}]
        }
        response = client.post("/api/sandbox/run", json=payload)
        assert response.status_code == 200
        assert response.json()["job_id"] == "test-123"
        assert "metrics" in response.json()
        assert "equity_curve" in response.json()

def test_ws_ticker_connection():
    """Testa a conexão do WebSocket de Ticker."""
    with client.websocket_connect("/api/ws/ticker") as websocket:
        # Recebe um frame para validar a serialização JSON (Auditoria 3.3)
        data = websocket.receive_json()
        assert data["symbol"] == "BTCUSDT"
        assert isinstance(data["price"], float)
        assert websocket is not None

def test_ws_pulse_connection():
    """Testa a conexão do WebSocket de Pulse (Logs)."""
    with client.websocket_connect("/api/ws/pulse") as websocket:
        assert websocket is not None

def test_get_system_logs():
    """Testa se o endpoint de logs retorna o histórico do arquivo."""
    with patch('backend.src.api.os.path.exists') as mock_exists:
        mock_exists.return_value = True
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                "Line 1\n", "Line 2\n", "ERROR: Test Error\n"
            ]
            response = client.get("/api/system/logs")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[2] == "ERROR: Test Error"
