import pytest
from unittest.mock import patch, MagicMock
import backend.src.config as config
config.GROK_API_DELAY_SECONDS = 0.0
from backend.src.ai.sentiment_analyzer import SentimentAnalyzer

@patch('backend.src.ai.sentiment_analyzer.requests.post')
def test_sentiment_analyzer_success(mock_post):
    # Mocking successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"score": 0.8, "label": "BULLISH"}'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    analyzer = SentimentAnalyzer()
    news_batch = ["Bitcoin hits new all time high", "Institutional adoption grows"]
    result = analyzer.analyze_batch(news_batch)

    assert result is not None
    assert result['score'] == 0.8
    assert result['label'] == "BULLISH"
    mock_post.assert_called_once()


@patch('backend.src.ai.sentiment_analyzer.requests.post')
@patch('backend.src.ai.sentiment_analyzer.time.sleep')
def test_sentiment_analyzer_rate_limit_handling(mock_sleep, mock_post):
    # Mocking 429 Too Many Requests on the first try, and success on the second
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429
    
    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"score": -0.5, "label": "BEARISH"}'
                }
            }
        ]
    }
    
    mock_post.side_effect = [mock_response_429, mock_response_200]

    analyzer = SentimentAnalyzer(max_retries=1, initial_backoff=0.1)
    news_batch = ["Market shows signs of weakness"]
    result = analyzer.analyze_batch(news_batch)

    assert result is not None
    assert result['score'] == -0.5
    assert result['label'] == "BEARISH"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@patch('backend.src.ai.sentiment_analyzer.requests.post')
@patch('backend.src.ai.sentiment_analyzer.time.sleep')
def test_sentiment_analyzer_rate_limit_exceeded(mock_sleep, mock_post):
    # Mocking persistent 429 Too Many Requests
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429
    mock_post.return_value = mock_response_429

    analyzer = SentimentAnalyzer(max_retries=2, initial_backoff=0.1)
    news_batch = ["Market shows signs of weakness"]
    
    # Should not raise exception, gracefully degrade by returning None
    result = analyzer.analyze_batch(news_batch)

    assert result is None
    assert mock_post.call_count == 3  # 1 initial + 2 retries
    assert mock_sleep.call_count == 2
