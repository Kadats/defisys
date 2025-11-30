"""
Data Layer - Handles all data collection, storage, and retrieval.

This package contains:
- sources.py: API data collectors (Binance, Deribit, FNG, etc.)
- storage.py: PostgreSQL database layer
- pipeline.py: Orchestrates data collection and storage
"""

__all__ = ['sources', 'storage', 'pipeline']
