import pytest
import json
from unittest.mock import patch, MagicMock
from backend.src.ai.llm_agent import (
    _extract_json_from_text,
    _fallback_decision,
    consult_risk_agent
)

def test_extract_json_from_text():
    # Plain JSON
    text = '{"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}'
    assert _extract_json_from_text(text) == {"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}
    
    # Markdown JSON
    text = '```json\n{"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}\n```'
    assert _extract_json_from_text(text) == {"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}
    
    # Markdown no language
    text = '```\n{"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}\n```'
    assert _extract_json_from_text(text) == {"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}
    
    # HTML code tags
    text = '<code>{"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}</code>'
    assert _extract_json_from_text(text) == {"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}
    
    # Extra text around JSON
    text = 'Sure, here is the JSON: {"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"} Hope it helps!'
    assert _extract_json_from_text(text) == {"action": "SPOT_ONLY", "amount_pct": 0.5, "reason": "test"}
    
    # Invalid JSON
    assert _extract_json_from_text("not json") is None

def test_fallback_decision():
    # Emergency defense: HF < 1.25
    ctx = {'health_factor': 1.1, 'rsi': 50, 'ml_confidence': 0.8}
    res = _fallback_decision(ctx)
    assert res['action'] == 'DEFENSE_MODE'
    assert res['amount_pct'] == 1.0
    
    # Extreme oversold: RSI < 30
    ctx = {'health_factor': 2.0, 'rsi': 25, 'ml_confidence': 0.4}
    res = _fallback_decision(ctx)
    assert res['action'] == 'SPOT_ONLY'
    assert res['amount_pct'] == 0.25
    
    # High confidence: ML > 0.75, HF > 2.0, RSI < 70
    ctx = {'health_factor': 2.5, 'rsi': 50, 'ml_confidence': 0.8}
    res = _fallback_decision(ctx)
    assert res['action'] == 'BORROW_AND_LP'
    assert res['amount_pct'] == 0.50
    
    # Overbought: RSI > 70, ML low
    ctx = {'health_factor': 2.0, 'rsi': 75, 'ml_confidence': 0.5}
    res = _fallback_decision(ctx)
    assert res['action'] == 'DO_NOTHING'
    
    # Default: No signal
    # TIER 7: 0.60 < ml and 35 <= rsi <= 70 -> SPOT_ONLY
    # To get DO_NOTHING, use rsi < 35 (but > 30) or rsi > 70 (but ML low)
    ctx = {'health_factor': 2.0, 'rsi': 32, 'ml_confidence': 0.5}
    res = _fallback_decision(ctx)
    assert res['action'] == 'DO_NOTHING'

@patch('backend.src.ai.llm_agent._consult_gemini')
def test_consult_risk_agent_api_success(mock_consult):
    mock_consult.return_value = {"action": "SPOT_ONLY", "amount_pct": 0.1, "reason": "api test"}
    ctx = {'health_factor': 2.0, 'rsi': 50, 'ml_confidence': 0.5}
    res = consult_risk_agent(ctx)
    assert res['action'] == 'SPOT_ONLY'
    assert res['reason'] == 'api test'

@patch('backend.src.ai.llm_agent._consult_gemini')
def test_consult_risk_agent_api_fail_fallback(mock_consult):
    mock_consult.return_value = None # API failed
    ctx = {'health_factor': 1.1, 'rsi': 50, 'ml_confidence': 0.5}
    res = consult_risk_agent(ctx)
    # Should use fallback_decision which returns DEFENSE_MODE for HF 1.1
    assert res['action'] == 'DEFENSE_MODE'
