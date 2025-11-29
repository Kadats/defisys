"""
Strategy Pattern implementation for trading strategies.

This package provides a modular approach to implementing different
trading strategies using the Strategy Pattern. Each strategy inherits
from BaseStrategy and implements the execute() method.
"""

from .base import BaseStrategy
from .btc_lite import BTCLiteStrategy, DAYS_OUT_OF_RANGE_THRESHOLD

__all__ = ['BaseStrategy', 'BTCLiteStrategy', 'DAYS_OUT_OF_RANGE_THRESHOLD']
