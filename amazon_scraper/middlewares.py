import random
import time
import logging
from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


class RotatingProxyMiddleware:
    """Assign a random proxy from a list to each request."""

    def __init__(self, proxy_list):
        self.proxy_list = proxy_list

    @classmethod
    def from_crawler(cls, crawler):
        proxy_list = crawler.settings.get('PROXY_LIST')
        return cls(proxy_list)

    def process_request(self, request, spider):
        if self.proxy_list:
            proxy = random.choice(self.proxy_list)
            request.meta['proxy'] = proxy
            logger.debug(f'Using proxy: {proxy}')
        # Rotate User-Agent
        request.headers['User-Agent'] = random.choice(USER_AGENTS)


class HumanTimingMiddleware:
    """
    Adds human-like delays between requests to avoid detection.
    Uses log-normal distribution timing instead of fixed delays.
    """

    def __init__(self, timing_enabled=True):
        self.timing_enabled = timing_enabled
        self._last_request_time = 0

    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('HUMAN_TIMING_ENABLED', True)
        return cls(enabled)

    def process_request(self, request, spider):
        if not self.timing_enabled:
            return

        import math
        now = time.time()
        if self._last_request_time > 0:
            # Log-normal distributed delay
            delay = random.lognormvariate(math.log(3.0), 0.5)
            delay = max(1.5, min(delay, 10.0))

            # Occasional hesitation (extra pause)
            if random.random() < 0.3:
                delay += random.uniform(1, 3)

            time.sleep(delay)

        self._last_request_time = time.time()
        logger.debug(f'Human timing delay: {delay:.2f}s')


class CustomRetryMiddleware(RetryMiddleware):
    def process_response(self, request, response, spider):
        if response.status in [403, 429]:
            reason = response_status_message(response.status)
            # Add longer delay on blocking
            import time
            time.sleep(random.uniform(5, 15))
            return self._retry(request, reason, spider) or response
        return response
