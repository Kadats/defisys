import pytest
from fastapi.testclient import TestClient

from backend.src.api import app

client = TestClient(app)


@pytest.mark.smoke
@pytest.mark.api
def test_paper_runtime_full_flow():
    stop_response = client.post("/api/paper/runtime/stop")
    assert stop_response.status_code == 200

    start_response = client.post(
        "/api/paper/runtime/start",
        json={"strategy_name": "accumulator", "environment": "paper"},
    )
    assert start_response.status_code == 200
    started = start_response.json()
    assert started["status"] == "started"
    assert started["session"]["environment"] == "paper"

    tick_response = client.post(
        "/api/paper/runtime/tick",
        json={
            "symbol": "BTCUSDT",
            "price": 65000.0,
            "source_status": "real",
            "ml_confidence": 0.8,
            "health_factor": 2.2,
            "kill_switch_active": False,
        },
    )
    assert tick_response.status_code == 200
    tick_body = tick_response.json()["result"]
    assert tick_body["runtime_status"] == "healthy"
    assert tick_body["decision_action"] in {"BUY", "HOLD"}

    status_response = client.get("/api/paper/runtime/status")
    assert status_response.status_code == 200
    status = status_response.json()
    assert status["running"] is True
    assert status["runtime_status"] in {"healthy", "degraded", "restricted", "halted"}

    events_response = client.get("/api/paper/runtime/events?limit=20")
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert len(events) > 0
    event_types = {event["event_type"] for event in events}
    assert "market_snapshot_received" in event_types
    assert "runtime_snapshot_emitted" in event_types


@pytest.mark.smoke
@pytest.mark.api
def test_paper_runtime_kill_switch_alert():
    client.post("/api/paper/runtime/stop")
    client.post("/api/paper/runtime/start", json={"strategy_name": "accumulator"})

    tick_response = client.post(
        "/api/paper/runtime/tick",
        json={
            "symbol": "BTCUSDT",
            "price": 64000.0,
            "source_status": "real",
            "ml_confidence": 0.9,
            "health_factor": 2.0,
            "kill_switch_active": True,
        },
    )
    assert tick_response.status_code == 200
    result = tick_response.json()["result"]
    assert result["runtime_status"] == "halted"
    assert result["decision_action"] == "BLOCKED"

    alerts_response = client.get("/api/paper/runtime/alerts?active_only=true")
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()["alerts"]
    assert len(alerts) > 0
    codes = {alert["code"] for alert in alerts}
    assert "KILL_SWITCH_ACTIVATED" in codes
