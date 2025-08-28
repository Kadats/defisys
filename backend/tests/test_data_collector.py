import json
import pytest
from types import SimpleNamespace

import backend.src.data_collector as dc


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            from requests.exceptions import HTTPError

            raise HTTPError(f"{self.status_code} Client Error")


def test_get_implied_volatility_history_happy_path(monkeypatch):
    payload = {"result": {"data": [{"timestamp": 1700000000000, "value": 42.0}, {"timestamp": 1700086400000, "value": 43.5}]}}

    def fake_get(path, params=None, headers=None, timeout=None):
        return DummyResponse(status_code=200, json_data=payload)

    monkeypatch.setattr(dc._deribit_client.session, "get", lambda url, params=None, headers=None, timeout=None: fake_get(url))

    out = dc.get_implied_volatility_history(index_name="BTC_DVOL", resolution="1D", start_timestamp_ms=1700000000000, end_timestamp_ms=1700086400000, limit=1000)
    assert isinstance(out, list)
    assert len(out) == 2
    assert out[0]["timestamp"] == 1700000000000
    assert abs(out[0]["volatility"] - 42.0) < 1e-6


def test_get_implied_volatility_history_400_returns_empty_and_logs(monkeypatch, caplog):
    def fake_get(path, params=None, headers=None, timeout=None):
        return DummyResponse(status_code=400, json_data={"error": "bad request"}, text="bad request")

    monkeypatch.setattr(dc._deribit_client.session, "get", lambda url, params=None, headers=None, timeout=None: fake_get(url))

    caplog.clear()
    out = dc.get_implied_volatility_history(index_name="BTC_DVOL", resolution="1D", start_timestamp_ms=1700000000000, end_timestamp_ms=1700086400000, limit=1000)
    assert out == []
    assert any("Erro ao conectar à API Deribit" in rec.message or "Resposta inesperada da Deribit" in rec.message for rec in caplog.records)


def test_get_implied_volatility_history_retries_on_503(monkeypatch):
    calls = {"count": 0}

    def fake_get(url, params=None, headers=None, timeout=None):
        # return 503 twice, then 200
        calls["count"] += 1
        if calls["count"] < 3:
            return DummyResponse(status_code=503, json_data={"error": "service unavailable"}, text="service unavailable")
        return DummyResponse(status_code=200, json_data={"result": {"data": [{"timestamp": 1700000000000, "value": 40.0}]}})

    monkeypatch.setattr(dc._deribit_client.session, "get", fake_get)

    out = dc.get_implied_volatility_history(index_name="BTC_DVOL", resolution="1D", start_timestamp_ms=1700000000000, end_timestamp_ms=1700086400000, limit=1000)
    assert isinstance(out, list)
    assert len(out) == 1
    assert calls["count"] >= 3
