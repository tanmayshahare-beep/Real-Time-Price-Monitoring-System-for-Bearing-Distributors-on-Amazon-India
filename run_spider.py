"""
Legacy entry point - redirects to orchestrator.
For direct use, prefer: python orchestrator.py --mode scheduled
"""
import subprocess
import schedule
import time
import random
import math
from dotenv import load_dotenv
import os

load_dotenv()

# Simple scheduler for backward compatibility
def run_spider():
    """Run a single scrape session with human-like timing."""
    query = os.getenv('TARGET_QUERY', 'SKF bearing 6205')
    print(f"Starting spider for: '{query}'")

    # Random session start delay
    start_delay = random.uniform(5, 15)
    print(f"Waiting {start_delay:.1f}s (human-like start delay)...")
    time.sleep(start_delay)

    result = subprocess.run(
        ["scrapy", "crawl", "amazon", "-a", f"query={query}"],
        timeout=300
    )

    if result.returncode == 0:
        print("Spider finished successfully.")
    else:
        print(f"Spider exited with code: {result.returncode}")

def run_analysis():
    """Run analysis on a known ASIN after scrape."""
    asin = os.getenv('MONITORED_ASIN', '')
    if not asin:
        print("No MONITORED_ASIN set, skipping analysis.")
        return

    print(f"Running analysis for ASIN: {asin}")
    try:
        result = subprocess.run(
            ["python", "-m", "analysis.analyze", asin],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.stdout:
            print(f"Analysis result:\n{result.stdout}")
    except Exception as e:
        print(f"Analysis failed: {e}")

# Schedule with jitter (human-like timing)
def get_interval_with_jitter():
    base_hours = float(os.getenv('SCRAPE_INTERVAL_HOURS', '6'))
    jitter_minutes = float(os.getenv('SCHEDULE_JITTER_MINUTES', '30'))
    jitter_seconds = random.uniform(-jitter_minutes, jitter_minutes) * 60
    return base_hours * 3600 + jitter_seconds

def schedule_next():
    interval = get_interval_with_jitter()
    print(f"Next scrape in {interval/3600:.2f} hours (with jitter)")
    schedule.every(interval).seconds.do(run_spider)

if __name__ == "__main__":
    print("Amazon Price Monitor - Legacy Scheduler")
    print("=" * 50)
    print("Note: For enhanced human-like behavior, use:")
    print("  python orchestrator.py --mode scheduled")
    print("=" * 50)

    run_spider()
    schedule_next()

    print("Scheduler started. Will run spider with randomized intervals.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nScheduler stopped.")
