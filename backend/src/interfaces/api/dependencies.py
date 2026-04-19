"""Centralized API dependencies and compatibility helpers for routers."""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd

from backend.src.application import TradingWorkflowUseCases
from backend.src.application.ports import SimulationRepositoryPort
from backend.src.ai import heuristics
from backend.src.infrastructure.repositories import default_simulation_repository
from backend.src.system_runner import (
    run_simulation as _run_simulation,
    run_trading_system as _run_trading_system,
    train_model_pipeline as _train_model_pipeline,
)
from backend.src.utils.analytics import calculate_yearly_metrics
from backend.src.config import DEFAULT_INTERVAL, DEFAULT_KLINES_LIMIT, DEFAULT_SYMBOL, PROJECT_ROOT

logger = logging.getLogger(__name__)

_SUMMARY_CACHE: dict = {}
_SIMULATION_RUNNING = False

_simulation_repository: SimulationRepositoryPort = default_simulation_repository

_use_cases = TradingWorkflowUseCases.from_callables(
    train_model_fn=_train_model_pipeline,
    run_simulation_fn=_run_simulation,
    run_system_fn=_run_trading_system,
)


def get_data_from_db(table_name: str, limit: int | None = None) -> pd.DataFrame:
    return _simulation_repository.get_klines(table_name, limit=limit)


def get_latest_simulation_summary():
    return _simulation_repository.get_latest_simulation_summary()


def get_positions_from_db(include_open: bool = True, include_closed: bool = True) -> pd.DataFrame:
    return _simulation_repository.get_positions(
        include_open=include_open,
        include_closed=include_closed,
    )


def get_predictions_from_db() -> pd.DataFrame:
    return _simulation_repository.get_predictions()


def train_model_pipeline():
    return _use_cases.train_model()


def run_simulation(
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = None,
    backtest_days: int | None = None,
    strategy_type: str = "accumulator",
    use_llm: bool = False,
):
    return _use_cases.run_simulation(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        backtest_days=backtest_days,
        strategy_type=strategy_type,
        use_llm=use_llm,
    )


def run_trading_system():
    return _use_cases.run_trading_system()


def run_sandbox_simulation(payload):
    """Execute isolated simulation for Sandbox Lab with realistic mock data."""
    logger.info("Sandbox Lab: Iniciando simulação com AI Confidence %s", payload.ai_confidence)

    current_equity = payload.initial_capital
    equity_curve = []
    start_date = datetime.now() - timedelta(days=30)
    trend = (payload.ai_confidence - 0.5) * 0.02

    for i in range(30):
        change = (random.random() - 0.5 + trend) * 0.02
        current_equity *= (1 + change)
        date_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        equity_curve.append({"date": date_str, "equity": round(current_equity, 2)})

    roi_total = ((current_equity / payload.initial_capital) - 1) * 100

    return {
        "success": True,
        "job_id": f"sandbox-{int(datetime.now().timestamp())}",
        "metrics": {
            "roi_total": round(roi_total, 2),
            "max_drawdown": round(random.uniform(5.0, 15.0), 2),
            "win_rate": round(random.uniform(55.0, 75.0), 2),
        },
        "equity_curve": equity_curve,
    }


def sanitize_for_json(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    return obj


def sanitize_df_for_json(df: pd.DataFrame) -> list:
    df = df.replace([np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), None)
    records = df.to_dict(orient="records")
    return sanitize_for_json(records)
