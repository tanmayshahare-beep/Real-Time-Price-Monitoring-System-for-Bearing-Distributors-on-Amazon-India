"""
Scrape Pattern Randomizer - Generates human-like scrape schedules and patterns.
Instead of always scraping the same query at fixed intervals, this introduces:
- Random decoy queries between target queries
- Variable timing between scrapes
- Rotating product check orders
- Occasional "warmup" scrapes (checking unrelated products)
"""
import logging
import random
import time
from typing import Dict, List, Optional, Tuple

from config import Config
from human_behavior import HumanTiming

logger = logging.getLogger(__name__)


class ScrapePatternRandomizer:
    """
    Generates human-like scrape patterns to avoid detection.
    Replaces the Etsy warmup concept with randomized scrape schedules.
    """

    def __init__(self, config: Config):
        self.config = config

    def generate_session_plan(self) -> Dict:
        """
        Generate a randomized scrape plan for this session.
        Determines order of queries, when to insert decoys, timing.

        Returns:
            Dictionary with session plan
        """
        seed = int(time.time()) % 10000
        rng = random.Random(seed)

        # Copy target queries and shuffle
        queries = list(self.config.TARGET_QUERIES)
        rng.shuffle(queries)

        # Decide where to insert decoy queries
        plan_queries = []
        for i, query in enumerate(queries):
            plan_queries.append(('target', query))

            # 40% chance of inserting a decoy after a target query
            if rng.random() < 0.4 and self.config.DECOY_QUERIES:
                decoy = rng.choice(self.config.DECOY_QUERIES)
                plan_queries.append(('decoy', decoy))

        # Randomize delays between queries
        delays = []
        for _ in range(len(plan_queries)):
            delay_min = rng.uniform(
                self.config.BETWEEN_SEARCHES_MIN,
                self.config.BETWEEN_SEARCHES_MAX
            )
            delays.append(delay_min)

        return {
            'queries': plan_queries,
            'delays': delays,
            'session_start_delay': rng.uniform(
                self.config.SESSION_START_DELAY_MIN,
                self.config.SESSION_START_DELAY_MAX
            )
        }

    def get_next_query(self, session_plan: Dict, current_index: int) -> Optional[Tuple[str, str]]:
        """
        Get the next query from the session plan.

        Args:
            session_plan: Plan from generate_session_plan()
            current_index: Current position in plan

        Returns:
            Tuple of (query_type, query_string) or None if done
        """
        queries = session_plan.get('queries', [])
        if current_index >= len(queries):
            return None
        return queries[current_index]

    def get_delay_for_next(self, session_plan: Dict, current_index: int) -> float:
        """
        Get the delay before the next query.

        Args:
            session_plan: Plan from generate_session_plan()
            current_index: Current position

        Returns:
            Delay in seconds
        """
        delays = session_plan.get('delays', [])
        if current_index >= len(delays):
            return 0
        base_delay = delays[current_index]
        # Add jitter
        return HumanTiming.jitter(base_delay, 0.15)

    def should_add_warmup(self) -> bool:
        """
        25% chance of doing a warmup scrape (checking unrelated products).
        This makes the pattern look more human to anti-bot systems.

        Returns:
            True if warmup/decoy scrape should be done
        """
        return random.random() < 0.25

    def get_warmup_query(self) -> str:
        """Get a random warmup/decoy query."""
        return self.config.get_random_decoy_query()


class DirectASINChecker:
    """
    Manages direct ASIN checks (bypassing search results).
    Introduces random ordering and timing for direct ASIN monitoring.
    """

    def __init__(self, config: Config):
        self.config = config

    def get_check_order(self) -> List[str]:
        """
        Get randomized order of ASINs to check.

        Returns:
            Shuffled list of ASINs
        """
        asins = list(self.config.MONITORED_ASINS)
        random.shuffle(asins)
        return asins

    def get_check_delay(self) -> float:
        """
        Get delay between ASIN checks (human-like timing).

        Returns:
            Delay in seconds
        """
        base = random.uniform(
            self.config.ASIN_CHECK_DELAY_MIN,
            self.config.ASIN_CHECK_DELAY_MAX
        )
        return HumanTiming.jitter(base, 0.2)

    def should_check_asin(self, asin: str) -> bool:
        """
        85% chance of checking an ASIN (sometimes skip to appear more human).

        Args:
            asin: ASIN to potentially check

        Returns:
            True if ASIN should be checked this round
        """
        return random.random() < 0.85


class BehavioralScheduler:
    """
    Combines human timing with scrape planning.
    Used by the spider to apply realistic delays between requests.
    """

    def __init__(self, config: Config):
        self.config = config
        self.timing = HumanTiming()

    def delay_before_request(self, page_type: str = 'default'):
        """
        Apply human-like delay before making next request.

        Args:
            page_type: 'search', 'product', 'offers', or 'default'
        """
        if page_type == 'search':
            self.timing.reading_time('short')
        elif page_type == 'product':
            self.timing.reading_time('medium')
        elif page_type == 'offers':
            self.timing.reading_time('long')
        else:
            self.timing.between_requests()

        # Occasional hesitation
        if self.timing.should_hesitate():
            self.timing.human_pause(1, 3)

    def delay_between_products(self):
        """Delay between checking different products."""
        self.timing.human_pause(
            self.config.REQUEST_DELAY_MIN,
            self.config.REQUEST_DELAY_MAX
        )

    def delay_session_start(self):
        """Apply delay when starting a new scrape session."""
        self.timing.session_start_delay()

    def delay_between_searches(self):
        """Apply delay between search queries."""
        self.timing.between_searches()
