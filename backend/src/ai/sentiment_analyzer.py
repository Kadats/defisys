import json
import logging
import time
from typing import List, Optional, Dict, Any
import requests

import backend.src.config as config

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self, max_retries: int = 3, initial_backoff: float = 2.0):
        self.api_key = config.GROK_API_KEY
        self.model = config.GROK_MODEL
        self.base_url = config.GROK_API_BASE_URL
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    def analyze_batch(self, news_batch: List[str]) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.warning("GROK_API_KEY not configured. Skipping sentiment analysis.")
            return None
        
        if not news_batch:
            return None

        prompt = (
            "Analyze the overall sentiment of the following crypto news batch.\n"
            "Return ONLY a JSON object with 'score' (float between -1.0 for bearish and 1.0 for bullish) "
            "and 'label' (string: 'BULLISH', 'BEARISH', or 'NEUTRAL').\n\n"
            "News:\n" + "\n- ".join(news_batch)
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a cryptocurrency market sentiment analyzer. You strictly output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0
        }

        backoff = self.initial_backoff
        for attempt in range(self.max_retries + 1):
            try:
                # Add delay to respect global RPM limits if configured
                if config.GROK_API_DELAY_SECONDS > 0 and attempt == 0:
                    time.sleep(config.GROK_API_DELAY_SECONDS)
                
                url = f"{self.base_url.rstrip('/')}/chat/completions"
                response = requests.post(url, headers=headers, json=data)

                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Clean potential markdown wrapping from response
                    content = content.replace("```json", "").replace("```", "").strip()
                    
                    try:
                        parsed_content = json.loads(content)
                        return {
                            "score": float(parsed_content.get("score", 0.0)),
                            "label": str(parsed_content.get("label", "NEUTRAL")).upper(),
                            "raw_response": content
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Grok API response as JSON: {content} - Error: {e}")
                        return None
                        
                elif response.status_code == 429:
                    if attempt < self.max_retries:
                        logger.warning(f"Grok API Rate Limit Exceeded (429). Retrying in {backoff} seconds...")
                        time.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error("Grok API Rate Limit Exceeded (429). Max retries reached. Gracefully degrading.")
                        return None
                else:
                    logger.error(f"Grok API returned error: {response.status_code} - {response.text}")
                    return None

            except requests.RequestException as e:
                logger.error(f"Network error when calling Grok API: {e}")
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    return None
            except Exception as e:
                logger.error(f"Unexpected error in sentiment analysis: {e}")
                return None
                
        return None
