from backend.src.config import DEFAULT_SYMBOL, LOG_LEVEL
from backend.src.logging_config import setup_logging


def test_config_defaults():
    assert DEFAULT_SYMBOL == "BTCUSDT"
    assert isinstance(LOG_LEVEL, str)


def test_setup_logging_returns_logger():
    logger = setup_logging()
    assert logger.name == "defisys"
    # Level should be set according to LOG_LEVEL (case-insensitive)
    assert logger.level in (20, 10, 30, 40, 50)
