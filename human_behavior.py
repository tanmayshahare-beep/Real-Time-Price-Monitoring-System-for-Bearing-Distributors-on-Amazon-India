"""
Human Behavior Utilities for Scrapy - Simulates realistic human timing patterns.
Adapted from Selenium-based interactions to work with Scrapy HTTP requests.
Provides randomized delays, request pacing, and anti-detection timing patterns.
"""
import math
import random
import time
from typing import Optional


class HumanTiming:
    """
    Realistic human timing patterns for web scraping.
    Instead of mouse movements, we simulate human-like request timing:
    - Variable pauses between requests (reading, thinking time)
    - Log-normal distributed delays (humans don't act at fixed intervals)
    - Occasional rapid requests (clicking through pages) vs long pauses (reading)
    - Session warming patterns
    """

    @staticmethod
    def human_pause(min_sec: float = 2.0, max_sec: float = 8.0) -> float:
        """
        Pause with log-normal distribution (mimics human thinking/reading time).
        Returns the actual pause duration for logging.

        Args:
            min_sec: Minimum pause duration
            max_sec: Maximum pause duration

        Returns:
            Actual pause duration in seconds
        """
        mean = (min_sec + max_sec) / 2
        std = (max_sec - min_sec) / 4
        pause = random.lognormvariate(math.log(mean), std / mean)
        actual_pause = max(min_sec, min(pause, max_sec))
        time.sleep(actual_pause)
        return actual_pause

    @staticmethod
    def between_requests() -> float:
        """
        Realistic delay between HTTP requests (like navigating between pages).
        Simulates time to click a link, wait for page to load, start reading.

        Returns:
            Actual delay in seconds
        """
        # Most humans take 2-10 seconds between page interactions
        delay = random.lognormvariate(math.log(4.0), 0.6)
        actual = max(1.5, min(delay, 12.0))
        time.sleep(actual)
        return actual

    @staticmethod
    def reading_time(content_length: str = 'medium') -> float:
        """
        Simulate time spent reading/scanning a page before next request.

        Args:
            content_length: 'short', 'medium', or 'long'

        Returns:
            Simulated reading time in seconds
        """
        ranges = {
            'short': (3.0, 10.0),    # Quick scan (search results)
            'medium': (8.0, 25.0),   # Reading product details
            'long': (15.0, 45.0),    # Detailed review (offers page, reviews)
        }
        min_t, max_t = ranges.get(content_length, (5.0, 15.0))
        return HumanTiming.human_pause(min_t, max_t)

    @staticmethod
    def session_start_delay() -> float:
        """
        Delay when starting a new scrape session (simulates user opening browser).

        Returns:
            Delay in seconds
        """
        delay = random.uniform(5.0, 15.0)
        time.sleep(delay)
        return delay

    @staticmethod
    def between_searches() -> float:
        """
        Delay between search queries (simulates thinking of next search).

        Returns:
            Delay in seconds
        """
        delay = random.lognormvariate(math.log(30.0), 0.5)
        actual = max(15.0, min(delay, 90.0))
        time.sleep(actual)
        return actual

    @staticmethod
    def rapid_succession(count: int = 3) -> list:
        """
        Simulate rapid page clicks (humans sometimes click through pages quickly).
        Returns list of short delays to apply between rapid requests.

        Args:
            count: Number of rapid requests expected

        Returns:
            List of delay values (seconds) to use between requests
        """
        delays = []
        for _ in range(count):
            d = random.uniform(0.5, 2.0)
            delays.append(d)
        return delays

    @staticmethod
    def random hesitation() -> bool:
        """
        30% chance of adding an extra pause (simulates human hesitation).
        Use before making a request to add unpredictability.

        Returns:
            True if hesitation should be applied
        """
        return random.random() < 0.3

    @staticmethod
    def jitter(base_delay: float, jitter_pct: float = 0.2) -> float:
        """
        Add random jitter to a fixed delay to avoid robotic patterns.

        Args:
            base_delay: Base delay in seconds
            jitter_pct: Percentage of base_delay to vary (+/-)

        Returns:
            Adjusted delay with jitter
        """
        jitter_amount = base_delay * jitter_pct
        return base_delay + random.uniform(-jitter_amount, jitter_amount)

    @staticmethod
    def simulate_session(minutes: int = 10):
        """
        Simulate a complete browsing session with human-like timing.
        Yields delay values for each step in the session.

        Args:
            minutes: Approximate session duration

        Yields:
            Delay values for each step
        """
        session_start = time.time()
        session_end = session_start + minutes * 60

        # Initial page load
        yield HumanTiming.human_pause(2, 5)

        while time.time() < session_end:
            action = random.choice(['search', 'browse', 'read', 'pause'])

            if action == 'search':
                # Time to type and submit search
                yield HumanTiming.human_pause(3, 8)
                # Rapid: click through results
                for d in HumanTiming.rapid_succession(2):
                    yield d
                # Read results page
                yield HumanTiming.reading_time('short')

            elif action == 'browse':
                # Click to product page
                yield HumanTiming.between_requests()
                # Read product
                yield HumanTiming.reading_time('medium')
                # Check offers
                yield HumanTiming.between_requests()
                yield HumanTiming.reading_time('long')

            elif action == 'read':
                # Just spend time on current page
                yield HumanTiming.reading_time('medium')

            else:
                # Random pause (distracted, switched tabs, etc.)
                yield HumanTiming.human_pause(10, 30)
