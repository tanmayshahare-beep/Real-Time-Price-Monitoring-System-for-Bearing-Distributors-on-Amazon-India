"""
Main Orchestrator for Amazon Price Monitor.
Manages the complete scrape-analyze lifecycle with human-like timing,
proxy rotation, staggered scheduling, and activity tracking.
"""
import logging
import random
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import Config
from warmup_manager import ScrapePatternRandomizer, BehavioralScheduler, DirectASINChecker
from logger import setup_logger, activity_logger, log_scrape_start, log_error, log_success
from stats import stats_tracker
from human_behavior import HumanTiming


class AmazonMonitorOrchestrator:
    """Orchestrates the complete monitoring cycle with anti-detection measures"""

    def __init__(self, config: Config):
        self.config = config
        self.pattern_randomizer = ScrapePatternRandomizer(config)
        self.behavior_scheduler = BehavioralScheduler(config)
        self.asin_checker = DirectASINChecker(config)
        self.logger = setup_logger(
            name='amazon_monitor',
            log_file=config.LOG_FILE,
            level=config.LOG_LEVEL
        )
        self.timing = HumanTiming()

    def setup_logging(self):
        """Configure logging (already done in __init__)"""
        pass

    def run_single_scrape(self, query: str, query_type: str = 'target') -> int:
        """
        Run a single Scrapy spider for a search query.
        Uses human-like timing before and after the scrape.

        Args:
            query: Search query string
            query_type: 'target' or 'decoy'

        Returns:
            Number of products scraped
        """
        self.logger.info(f"Running scrape for '{query}' ({query_type})")
        activity_logger.log_session_start(query)
        stats_tracker.start_query(query)

        # Human-like delay before starting
        if query_type == 'target':
            self.behavior_scheduler.delay_session_start()
        else:
            self.timing.human_pause(5, 15)

        # Run the spider
        try:
            result = subprocess.run(
                ['scrapy', 'crawl', 'amazon', '-a', f'query={query}'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                # Parse output for product count
                products_found = 0
                for line in result.stdout.split('\n'):
                    if 'Scraped' in line or 'product' in line.lower():
                        products_found += 1

                activity_logger.log_session_end(query, products_found)
                self.logger.info(f"Scrape complete for '{query}': {products_found} products")
                return products_found
            else:
                error_msg = result.stderr[:200] if result.stderr else 'Unknown error'
                self.logger.error(f"Scrape failed for '{query}': {error_msg}")
                activity_logger.log_error(query, error_msg, 'Scrapy run')
                stats_tracker.log_error(query, error_msg)
                return 0

        except subprocess.TimeoutExpired:
            self.logger.error(f"Scrape timed out for '{query}'")
            activity_logger.log_error(query, 'Timeout expired', 'Scrapy run')
            stats_tracker.log_error(query, 'Timeout expired', 'Scrape')
            return 0

        except Exception as e:
            self.logger.error(f"Unexpected error during scrape for '{query}': {e}")
            activity_logger.log_error(query, str(e), 'Scrape')
            stats_tracker.log_error(query, str(e))
            return 0

    def run_analysis_for_asins(self, asins: List[str]):
        """
        Run AI analysis for a list of ASINs.

        Args:
            asins: List of ASINs to analyze
        """
        for asin in asins:
            try:
                self.logger.info(f"Running AI analysis for ASIN: {asin}")
                activity_logger.log_session_start(f"analysis-{asin}")

                result = subprocess.run(
                    ['python', '-m', 'analysis.analyze', asin],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode == 0:
                    recommendation = result.stdout.strip()
                    activity_logger.log_analysis(asin, recommendation)
                    stats_tracker.log_analysis(asin, recommendation)
                    self.logger.info(f"Analysis complete for {asin}")
                else:
                    self.logger.warning(f"Analysis failed for {asin}: {result.stderr[:200]}")

                # Delay between analyses
                self.timing.human_pause(10, 30)

            except Exception as e:
                self.logger.error(f"Analysis error for {asin}: {e}")
                activity_logger.log_error(asin, str(e), 'Analysis')

    def run_session(self):
        """
        Run a complete monitoring session with human-like patterns.
        Generates a random plan, executes scrapes, runs analysis.
        """
        self.logger.info("Starting monitoring session")
        stats_tracker.initialize_session(self.config.TARGET_QUERIES)

        # Generate randomized session plan
        session_plan = self.pattern_randomizer.generate_session_plan()
        self.logger.info(f"Session plan: {len(session_plan['queries'])} queries planned")

        # Check if we should do warmup/decoy scrapes first
        if self.pattern_randomizer.should_add_warmup():
            warmup_query = self.pattern_randomizer.get_warmup_query()
            self.logger.info(f"Running warmup/decoy scrape: '{warmup_query}'")
            self.run_single_scrape(warmup_query, 'decoy')
            self.behavior_scheduler.delay_between_searches()

        # Execute planned queries
        for i, (query_type, query) in enumerate(session_plan['queries']):
            # Apply delay before each query
            if i > 0:
                delay = self.pattern_randomizer.get_delay_for_next(session_plan, i - 1)
                self.logger.info(f"Waiting {delay:.0f}s before next query...")
                self.timing.human_pause(
                    max(10, delay - 10),
                    delay + 10
                )

            # Run the scrape
            products = self.run_single_scrape(query, query_type)

            # Occasional extra decoy scrape
            if self.pattern_randomizer.should_add_warmup() and query_type == 'target':
                decoy = self.pattern_randomizer.get_warmup_query()
                self.logger.info(f"Adding extra decoy scrape: '{decoy}'")
                self.run_single_scrape(decoy, 'decoy')
                self.behavior_scheduler.delay_between_searches()

        # Run analysis on monitored ASINs if available
        if self.config.MONITORED_ASINS:
            self.logger.info("Running post-scrape analysis on monitored ASINs")
            analysis_asins = [
                asin for asin in self.config.MONITORED_ASINS
                if self.asin_checker.should_check_asin(asin)
            ]
            if analysis_asins:
                self.run_analysis_for_asins(analysis_asins)

        # Export session report
        report_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        stats_tracker.export_report(report_file)
        self.logger.info(f"Session complete. Report saved to {report_file}")

    def run_scheduled_monitoring(self):
        """
        Run continuous monitoring on a schedule with jitter.
        Replaces the simple scheduler in run_spider.py with human-like timing.
        """
        self.logger.info("Starting scheduled monitoring (human-like timing)")

        while True:
            try:
                # Run a full session
                self.run_session()

                # Calculate next run time with jitter
                base_interval = self.config.SCRAPE_INTERVAL_HOURS * 3600
                jitter = self.config.get_session_jitter()
                next_run = base_interval + jitter

                self.logger.info(
                    f"Next session in {next_run/3600:.1f} hours "
                    f"(base: {self.config.SCRAPE_INTERVAL_HOURS}h, jitter: {jitter/60:.0f}m)"
                )

                # Sleep in increments (so we can respond to interrupts)
                sleep_remaining = next_run
                while sleep_remaining > 0:
                    sleep_chunk = min(300, sleep_remaining)  # 5 min chunks
                    time.sleep(sleep_chunk)
                    sleep_remaining -= sleep_chunk

            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
                activity_logger.log_error('orchestrator', str(e), 'Monitoring cycle')
                # Wait before retrying
                self.timing.human_pause(30, 60)

    def run_direct_asin_checks(self):
        """
        Run direct ASIN checks (bypassing search).
        Useful for monitoring specific products you already know.
        """
        self.logger.info("Starting direct ASIN monitoring")
        stats_tracker.initialize_session(self.config.MONITORED_ASINS)

        check_order = self.asin_checker.get_check_order()

        for i, asin in enumerate(check_order):
            if not self.asin_checker.should_check_asin(asin):
                self.logger.info(f"Skipping ASIN {asin} this round")
                continue

            # Apply delay between checks
            if i > 0:
                delay = self.asin_checker.get_check_delay()
                self.logger.info(f"Waiting {delay:.0f}s before next ASIN check...")
                self.timing.human_pause(max(15, delay - 10), delay + 10)

            # Run spider for specific ASIN (requires spider modification)
            try:
                self.logger.info(f"Checking ASIN: {asin}")
                activity_logger.log_session_start(asin)

                result = subprocess.run(
                    ['scrapy', 'crawl', 'amazon', '-a', f'asin={asin}'],
                    capture_output=True,
                    text=True,
                    timeout=180
                )

                if result.returncode == 0:
                    activity_logger.log_session_end(asin, 1)
                    stats_tracker.log_scrape(asin, success=True)
                else:
                    self.logger.warning(f"ASIN check failed: {asin}")
                    stats_tracker.log_scrape(asin, success=False)

            except Exception as e:
                self.logger.error(f"Error checking ASIN {asin}: {e}")
                stats_tracker.log_error(asin, str(e))

        # Run analysis
        if self.config.MONITORED_ASINS:
            self.run_analysis_for_asins(self.config.MONITORED_ASINS)

        self.logger.info("Direct ASIN monitoring complete")


# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    config = Config()
    monitor = AmazonMonitorOrchestrator(config)

    import argparse

    parser = argparse.ArgumentParser(description='Amazon Price Monitor Orchestrator')
    parser.add_argument(
        '--mode',
        choices=['once', 'scheduled', 'direct-asin'],
        default='once',
        help='Run mode: once (single session), scheduled (continuous), direct-asin (check specific ASINs)'
    )
    args = parser.parse_args()

    try:
        if args.mode == 'once':
            monitor.run_session()
        elif args.mode == 'scheduled':
            monitor.run_scheduled_monitoring()
        elif args.mode == 'direct-asin':
            monitor.run_direct_asin_checks()
    except KeyboardInterrupt:
        logging.info("Monitor stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        raise
