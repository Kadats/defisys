"""
Agentic Risk Manager - Google Gemini API Integration.

This module integrates with Google Gemini API to make LLM-based risk management decisions.
Uses JSON Mode to force structured responses.

Current: Google Gemini 2.5 Flash (fast, low-cost, stable JSON output)
Fallback: Deterministic heuristic-based decision making if API fails
Requires: google-generativeai >= 0.7.2 (avoid 0.4.1 which has compatibility issues)
"""

import logging
import json
import os
import time
from typing import Dict, Optional, Any

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)

# Default model can be overridden via env (e.g., models/gemini-2.5-flash)
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "models/gemini-2.5-flash")

# Delay between API calls to respect rate limits (15 RPM = 4s per request)
# Default: 5s (conservative) - can be overridden via GEMINI_API_DELAY_SECONDS
GEMINI_API_DELAY = float(os.environ.get("GEMINI_API_DELAY_SECONDS", "5.0"))


def _select_gemini_model(preferred_models: list[str]) -> Optional[str]:
    """
    Pick the first available model that supports generateContent.
    Falls back to the first preferred model if listing fails.
    """
    try:
        available_models: list[str] = []
        for model in genai.list_models():
            if "generateContent" in getattr(model, "supported_generation_methods", []):
                available_models.append(model.name)

        for model_name in preferred_models:
            if model_name in available_models:
                return model_name

        if available_models:
            return available_models[0]
        return None
    except Exception as exc:
        logger.warning("[GEMINI] Failed to list models: %s", exc)
        return preferred_models[0] if preferred_models else None

# Configure Gemini API
MODEL = None
if GEMINI_AVAILABLE:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key, transport="rest")
            preferred_models = [
                DEFAULT_GEMINI_MODEL,
                "models/gemini-2.5-flash",
                "models/gemini-2.0-flash",
                "models/gemini-pro-latest",
                "models/gemini-flash-latest",
            ]
            model_name = _select_gemini_model(preferred_models)
            if not model_name:
                raise RuntimeError("No Gemini models available for generateContent")

            MODEL = genai.GenerativeModel(
                model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                    response_mime_type="application/json",
                )
            )
            logger.info("[GEMINI] API configured successfully with %s", model_name)
        except Exception as e:
            logger.warning("[GEMINI] Failed to configure API: %s. Will use fallback.", e)
            GEMINI_AVAILABLE = False
            MODEL = None
    else:
        logger.warning("[GEMINI] GEMINI_API_KEY not found. Using fallback mode.")
        GEMINI_AVAILABLE = False
else:
    logger.warning("[GEMINI] google-generativeai not installed. Using fallback mode.")

# System Prompt - The Soul of the Risk Manager
SYSTEM_PROMPT = """You are an Expert DeFi Risk Manager AI. Your role is to analyze market and portfolio conditions and recommend the optimal trading action.

CONTEXT INPUT:
- usd_balance: Available USD capital
- btc_collateral: BTC held as collateral
- aave_debt: Total debt in USD
- health_factor: Aave health factor (liquidation at <1.25, danger at <1.5)
- ml_confidence: ML model confidence (0.0 to 1.0)
- rsi: Relative Strength Index (0-100, <30 oversold, >70 overbought)

POSSIBLE ACTIONS:
1. DEFENSE_MODE: Close all leverage, repay debt, de-risk. Use when HF is low or liquidation risk is high.
2. BORROW_AND_LP: Aggressive DeFi strategy. Borrow USDT, open LPs, leverage yield. Use when ML confidence is high and HF is safe.
3. CONSERVATIVE_LP: Moderate yield farming without aggressive borrowing. Use for medium-confidence signals.
4. SPOT_ONLY: Simple BTC accumulation without leverage. Use when oversold or low confidence.
5. DO_NOTHING: Maintain current positions. Wait for better conditions.

DECISION LOGIC:
- If health_factor < 1.25: Choose DEFENSE_MODE (critical liquidation risk).
- If health_factor < 1.5: Choose DEFENSE_MODE (reduce risk).
- If RSI < 30: Prefer SPOT_ONLY (extreme oversold, accumulate).
- If RSI > 70 and ML < 0.65: Choose DO_NOTHING (overbought, low conviction).
- If ML > 0.75 and HF > 2.0: Choose BORROW_AND_LP (high confidence, safe to leverage).
- If 0.60 < ML <= 0.75 and HF > 1.8: Choose CONSERVATIVE_LP (medium confidence, moderate risk).
- If ML <= 0.60: Choose SPOT_ONLY or DO_NOTHING (low conviction).

RESPONSE FORMAT:
Return ONLY valid JSON with no additional text:
{
    "action": "BORROW_AND_LP" | "CONSERVATIVE_LP" | "SPOT_ONLY" | "DEFENSE_MODE" | "DO_NOTHING",
    "amount_pct": 0.0 to 1.0 (recommended allocation percentage),
    "reason": "Brief explanation of decision (max 100 chars)"
}

CRITICAL RULES:
- action must be one of the 5 valid options.
- amount_pct must be a float between 0.0 and 1.0.
- reason must be a concise string.
- RESPOND WITH JSON ONLY. NO OTHER TEXT."""


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from model output text."""
    if not text:
        return None

    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(cleaned[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    return None


def _consult_gemini(context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Consult Google Gemini API for risk management decision.
    
    Args:
        context: Market and portfolio data
    
    Returns:
        Dictionary with action, amount_pct, reason, or None if API fails
    """
    if not GEMINI_AVAILABLE or MODEL is None:
        logger.debug("[GEMINI] API not available, using fallback")
        return None
    
    try:
        # Format context for the prompt
        context_str = f"""{SYSTEM_PROMPT}

Current Market & Portfolio State:
- USD Balance: ${context.get('usd_balance', 0):.2f}
- BTC Collateral: {context.get('btc_collateral', 0):.6f} BTC
- Aave Debt: ${context.get('aave_debt', 0):.2f}
- Health Factor: {context.get('health_factor', 999):.2f}
- ML Model Confidence: {context.get('ml_confidence', 0.5):.2%}
- RSI: {context.get('rsi', 50):.1f}

Analyze this state and recommend the best action. Return ONLY valid JSON."""
        
        # Call Gemini API (generation_config already set in MODEL initialization)
        # Retry with exponential backoff for rate limits (429)
        max_retries = 3
        api_call_successful = False
        for attempt in range(max_retries):
            try:
                logger.debug("[GEMINI] Calling API with context... (attempt %d/%d)", attempt + 1, max_retries)
                response = MODEL.generate_content(context_str)
                api_call_successful = True
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e)
                # Check for rate limit error
                if "429" in error_str or "TooManyRequests" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                        logger.warning("[GEMINI] Rate limit hit (429), retrying in %ds... (%d/%d)", 
                                      wait_time, attempt + 1, max_retries)
                        time.sleep(wait_time)
                        continue
                # Non-retryable error or max retries exceeded
                raise
        
        # Parse JSON response
        response_text = response.text.strip()
        logger.debug("[GEMINI] Raw response: %s", response_text[:200])

        result = _extract_json_from_text(response_text)

        # Validate response structure
        if not isinstance(result, dict):
            logger.error("[GEMINI] Response is not valid JSON dict")
            return None
        
        action = result.get("action", "").upper()
        valid_actions = {"SPOT_ONLY", "BORROW_AND_LP", "CONSERVATIVE_LP", "DEFENSE_MODE", "DO_NOTHING"}
        
        if action not in valid_actions:
            logger.error(f"[GEMINI] Invalid action: {action}")
            return None
        
        amount_pct = float(result.get("amount_pct", 0.0))
        if not 0.0 <= amount_pct <= 1.0:
            logger.warning(f"[GEMINI] Amount_pct out of range: {amount_pct}, clamping")
            amount_pct = max(0.0, min(1.0, amount_pct))
        
        reason = str(result.get("reason", "No reason provided"))[:100]
        
        logger.info(
            f"[GEMINI] Decision: {action} | Amount: {amount_pct:.0%} | {reason}"
        )
        
        # Sleep to respect API rate limits (15 RPM = 4s between calls)
        # Only sleep if API call was successful (not during retry delays)
        if api_call_successful and GEMINI_API_DELAY > 0:
            logger.debug("[GEMINI] Waiting %.1fs to respect rate limit (15 RPM)...", GEMINI_API_DELAY)
            time.sleep(GEMINI_API_DELAY)
        
        return {
            "action": action,
            "amount_pct": amount_pct,
            "reason": reason,
        }
    
    except Exception as e:
        logger.error(
            "[GEMINI] API Error: %s: %s. Will use fallback.",
            type(e).__name__,
            str(e)[:150],
        )
        return None


def _fallback_decision(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback heuristic decision making when Gemini API is unavailable.
    Replicates the logic from the original mock implementation.
    
    Args:
        context: Market and portfolio data
    
    Returns:
        Dictionary with action, amount_pct, reason
    """
    # Extract context with safe defaults
    rsi = float(context.get('rsi', 50.0))
    health_factor = float(context.get('health_factor', 999.0))
    ml_confidence = float(context.get('ml_confidence', 0.5))
    
    # Validate ranges
    rsi = max(0.0, min(100.0, rsi))
    ml_confidence = max(0.0, min(1.0, ml_confidence))
    health_factor = max(0.1, health_factor)
    
    logger.warning("[FALLBACK] Using heuristic decision logic (Gemini API unavailable)")
    
    # --- TIER 1: EMERGENCY DEFENSE ---
    if health_factor < 1.25:
        return {
            'action': 'DEFENSE_MODE',
            'amount_pct': 1.0,
            'reason': f'Critical HF ({health_factor:.2f}). Liquidation risk. Closing all.',
        }
    
    # --- TIER 2: CONSERVATIVE DEFENSE MODE ---
    if health_factor < 1.5:
        return {
            'action': 'DEFENSE_MODE',
            'amount_pct': 0.6,
            'reason': f'Low HF ({health_factor:.2f}). Reducing leverage exposure.',
        }
    
    # --- TIER 3: EXTREME OVERSOLD ---
    if rsi < 30:
        return {
            'action': 'SPOT_ONLY',
            'amount_pct': 0.25,
            'reason': f'Extreme oversold (RSI={rsi:.1f}). Conservative spot buy.',
        }
    
    # --- TIER 4: OVERBOUGHT CONDITIONS ---
    if rsi > 70:
        if ml_confidence > 0.65:
            return {
                'action': 'SPOT_ONLY',
                'amount_pct': 0.15,
                'reason': f'Overbought (RSI={rsi:.1f}) but high ML confidence.',
            }
        else:
            return {
                'action': 'DO_NOTHING',
                'amount_pct': 0.0,
                'reason': f'Overbought (RSI={rsi:.1f}) and low ML confidence.',
            }
    
    # --- TIER 5: BULLISH CONDITIONS ---
    if ml_confidence > 0.75 and health_factor > 2.0 and rsi < 70:
        return {
            'action': 'BORROW_AND_LP',
            'amount_pct': 0.50,
            'reason': f'High ML ({ml_confidence:.2%}) + safe HF ({health_factor:.2f}).',
        }
    
    # --- TIER 6: MODERATE BULLISH ---
    if 0.60 < ml_confidence <= 0.75 and health_factor > 1.8 and rsi < 65:
        return {
            'action': 'CONSERVATIVE_LP',
            'amount_pct': 0.35,
            'reason': f'Medium ML ({ml_confidence:.2%}) + good conditions.',
        }
    
    # --- TIER 7: WEAK SIGNAL ---
    if ml_confidence <= 0.60 and 35 <= rsi <= 70:
        return {
            'action': 'SPOT_ONLY',
            'amount_pct': 0.10,
            'reason': f'Low ML ({ml_confidence:.2%}). Minimal spot buy.',
        }
    
    # --- TIER 8: NO SIGNAL ---
    return {
        'action': 'DO_NOTHING',
        'amount_pct': 0.0,
        'reason': f'No clear signal. ML={ml_confidence:.2%}, RSI={rsi:.1f}.',
    }


def consult_risk_agent(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consult the Risk Agent (LLM or Fallback) for a trade decision.
    
    This function attempts to use Google Gemini API for intelligent risk management.
    If the API is unavailable or fails, it automatically falls back to heuristic decision making.
    
    Args:
        context: Dictionary containing market and portfolio data
    
    Returns:
        Dictionary with:
            - action: One of [SPOT_ONLY, BORROW_AND_LP, CONSERVATIVE_LP, DEFENSE_MODE, DO_NOTHING]
            - amount_pct: Recommended allocation percentage (0.0 to 1.0)
            - reason: Human-readable explanation
    """
    # Try Gemini API first
    if GEMINI_AVAILABLE:
        gemini_result = _consult_gemini(context)
        if gemini_result is not None:
            return gemini_result
    
    # Fall back to heuristic if API fails or unavailable
    return _fallback_decision(context)

