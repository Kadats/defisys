"""
Base Strategy abstract class.

Defines the interface that all trading strategies must implement.
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.src.core import TradingEngine


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    
    All strategies must implement the execute() method which contains
    the trading logic for a single time step.
    """
    
    @abstractmethod
    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> dict:
        """
        Execute the strategy logic for a single time step.
        
        Args:
            row: Current market data (OHLCV + indicators)
            engine: TradingEngine instance with portfolio state
            timestamp: Current timestamp
            
        Returns:
            dict: Decision object containing:
                  - action (str): Action taken (e.g., 'BUY', 'SELL', 'HOLD', 'OPEN_LP')
                  - sizing (float): Sizing of the action
                  - reason (str): Reason for the action
                  - expected_risk (str): Expected risk ('Low', 'Med', 'High')
        """
        pass
    
    def get_name(self) -> str:
        """
        Return the strategy name.
        
        Returns:
            Strategy name (defaults to class name)
        """
        return self.__class__.__name__
