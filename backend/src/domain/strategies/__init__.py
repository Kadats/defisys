"""Canonical strategy package for domain-level strategy logic."""

from .base import BaseStrategy
from .btc_lite import BTCLiteStrategy, DAYS_OUT_OF_RANGE_THRESHOLD
from .accumulator import AccumulatorStrategy
from .swing_usd import SwingUSDStrategy
from .pure_spot import PureSpotStrategy
from .smart_dca import SmartDCAStrategy
from .short_strategy import AggressiveShortStrategy
from .yield_manager import AaveYieldManager
from .factory import build_strategy

__all__ = [
    "BaseStrategy",
    "BTCLiteStrategy",
    "AccumulatorStrategy",
    "SwingUSDStrategy",
    "PureSpotStrategy",
    "SmartDCAStrategy",
    "AggressiveShortStrategy",
    "AaveYieldManager",
    "DAYS_OUT_OF_RANGE_THRESHOLD",
    "build_strategy",
]
