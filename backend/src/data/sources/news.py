import logging
from typing import List

logger = logging.getLogger(__name__)

def fetch_mock_news_batch() -> List[str]:
    """
    Mocks fetching a batch of news from RSS feeds or APIs.
    In a real scenario, this would group articles to avoid multiple API calls.
    """
    logger.info("Fetching mock news batch for sentiment analysis")
    return [
        "Bitcoin continues to show strong momentum after recent ETF approval.",
        "Regulatory concerns ease as SEC provides clearer guidance on crypto.",
        "Institutional accumulation of BTC reaches new all-time highs.",
        "Some analysts warn of potential short-term pullback due to overbought conditions.",
        "Ethereum upgrades drive network efficiency, boosting broader market confidence."
    ]
