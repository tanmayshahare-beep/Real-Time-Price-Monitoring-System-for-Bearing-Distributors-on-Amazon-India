"""
Central configuration for Amazon Price Monitoring Bot.
Manages scraper settings, behavioral timing, scheduling, and environment.
"""
import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration for Amazon Price Monitor"""

    # ==================== Amazon Settings ====================
    AMAZON_DOMAIN = os.getenv('AMAZON_DOMAIN', 'amazon.in')
    AMAZON_BASE_URL = f"https://www.{AMAZON_DOMAIN}"

    # Search queries to rotate through (makes behavior less robotic)
    TARGET_QUERIES: List[str] = [
        q.strip() for q in os.getenv(
            'TARGET_QUERIES',
            'SKF bearing 6205'
        ).split(',') if q.strip()
    ]

    # Additional decoy queries (searched randomly to appear more human)
    DECOY_QUERIES: List[str] = [
        q.strip() for q in os.getenv(
            'DECOY_QUERIES',
            'bearing 6204, SKF 6305 bearing, NSK bearing 6206, FAG bearing 6205'
        ).split(',') if q.strip()
    ]

    # Specific ASINs to monitor directly
    MONITORED_ASINS: List[str] = [
        asin.strip() for asin in os.getenv('MONITORED_ASINS', '').split(',')
        if asin.strip()
    ]

    # ==================== MongoDB Settings ====================
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB = os.getenv('MONGO_DB', 'amazon_pricing')

    # ==================== Proxy Settings ====================
    _proxy_list = os.getenv('PROXY_LIST', '')
    PROXY_LIST: List[str] = [
        p.strip() for p in _proxy_list.split(',') if p.strip()
    ]
    PROXY_ROTATION_ENABLED = os.getenv('PROXY_ROTATION_ENABLED', 'true').lower() == 'true'

    # ==================== Ollama / AI Settings ====================
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv(
        'OLLAMA_MODEL',
        'hf.co/quelmap/Lightning-4b-GGUF-short-ctx:Q4_K_M'
    )

    # ==================== Scheduling ====================
    SCRAPE_INTERVAL_HOURS = float(os.getenv('SCRAPE_INTERVAL_HOURS', '6'))
    # Add jitter to schedule (± minutes)
    SCHEDULE_JITTER_MINUTES = float(os.getenv('SCHEDULE_JITTER_MINUTES', '30'))

    # Stagger multiple ASIN checks (seconds between each)
    ASIN_CHECK_DELAY_MIN = float(os.getenv('ASIN_CHECK_DELAY_MIN', '30'))
    ASIN_CHECK_DELAY_MAX = float(os.getenv('ASIN_CHECK_DELAY_MAX', '120'))

    # ==================== Behavioral Timing (Human-like) ====================
    # Delay between page requests during a scrape session
    REQUEST_DELAY_MIN = float(os.getenv('REQUEST_DELAY_MIN', '2'))
    REQUEST_DELAY_MAX = float(os.getenv('REQUEST_DELAY_MAX', '8'))

    # Reading time on different page types
    READING_TIME_SEARCH_MIN = float(os.getenv('READING_TIME_SEARCH_MIN', '3'))
    READING_TIME_SEARCH_MAX = float(os.getenv('READING_TIME_SEARCH_MAX', '10'))
    READING_TIME_PRODUCT_MIN = float(os.getenv('READING_TIME_PRODUCT_MIN', '8'))
    READING_TIME_PRODUCT_MAX = float(os.getenv('READING_TIME_PRODUCT_MAX', '25'))
    READING_TIME_OFFERS_MIN = float(os.getenv('READING_TIME_OFFERS_MIN', '15'))
    READING_TIME_OFFERS_MAX = float(os.getenv('READING_TIME_OFFERS_MAX', '45'))

    # Between searches delay
    BETWEEN_SEARCHES_MIN = float(os.getenv('BETWEEN_SEARCHES_MIN', '15'))
    BETWEEN_SEARCHES_MAX = float(os.getenv('BETWEEN_SEARCHES_MAX', '90'))

    # Session start delay
    SESSION_START_DELAY_MIN = float(os.getenv('SESSION_START_DELAY_MIN', '5'))
    SESSION_START_DELAY_MAX = float(os.getenv('SESSION_START_DELAY_MAX', '15'))

    # Hesitation probability (extra random pause before action)
    HESITATION_PROBABILITY = float(os.getenv('HESITATION_PROBABILITY', '0.3'))

    # ==================== Scrapy Settings ====================
    BOT_NAME = 'amazon_scraper'
    ROBOTSTXT_OBEY = False
    CONCURRENT_REQUESTS = int(os.getenv('CONCURRENT_REQUESTS', '4'))
    DOWNLOAD_DELAY = int(os.getenv('DOWNLOAD_DELAY', '2'))
    RANDOMIZE_DOWNLOAD_DELAY = True

    # Retry settings
    RETRY_TIMES = int(os.getenv('RETRY_TIMES', '5'))
    RETRY_HTTP_CODES = [500, 502, 503, 504, 403, 429, 408]

    # ==================== Logging ====================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'amazon_scraper.log')
    ACTIVITY_LOG_FILE = os.getenv('ACTIVITY_LOG_FILE', 'activity.log')

    # ==================== Stats ====================
    STATS_FILE = os.getenv('STATS_FILE', 'bot_stats.json')

    # ==================== User Agents ====================
    USER_AGENTS: List[str] = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    @classmethod
    def get_random_decoy_query(cls) -> str:
        """Get a random decoy query for human-like behavior."""
        import random
        if cls.DECOY_QUERIES:
            return random.choice(cls.DECOY_QUERIES)
        return cls.TARGET_QUERIES[0] if cls.TARGET_QUERIES else 'bearing'

    @classmethod
    def get_session_jitter(cls) -> float:
        """Get jitter in seconds for scheduled scrape time."""
        import random
        return random.uniform(
            -cls.SCHEDULE_JITTER_MINUTES * 60,
            cls.SCHEDULE_JITTER_MINUTES * 60
        )
