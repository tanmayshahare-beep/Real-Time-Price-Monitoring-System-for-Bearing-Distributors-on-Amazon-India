"""
Statistics Tracker for Amazon Price Monitor.
Tracks scrape sessions, products monitored, price changes, errors, and progress.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ProductStats:
    """Statistics for a single ASIN"""
    asin: str
    title: str = ''
    first_seen: str = ''
    last_scraped: str = ''
    scrape_count: int = 0
    current_price: str = '0'
    lowest_price: str = '0'
    highest_price: str = '0'
    price_changes: int = 0
    sellers_seen: int = 0
    errors: int = 0
    status: str = 'pending'  # pending, scraping, scraped, error


@dataclass
class SessionStats:
    """Overall session statistics"""
    start_time: str = ''
    queries_run: int = 0
    products_total: int = 0
    products_scraped: int = 0
    products_failed: int = 0
    total_sellers_found: int = 0
    total_price_changes: int = 0
    total_errors: int = 0
    analyses_run: int = 0
    current_query: str = ''


class StatsTracker:
    """Tracks and manages monitoring statistics"""

    def __init__(self, stats_file: str = 'bot_stats.json'):
        self.stats_file = Path(stats_file)
        self.session = SessionStats()
        self.products: Dict[str, ProductStats] = {}
        self.activity_history: List[Dict] = []
        self.start_time = time.time()
        self._load_stats()

    def _load_stats(self):
        """Load existing stats from file"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.session = SessionStats(**data.get('session', {}))

                    for asin, prod_data in data.get('products', {}).items():
                        self.products[asin] = ProductStats(**prod_data)

                    self.activity_history = data.get('activity_history', [])
            except Exception as e:
                print(f"Warning: Could not load stats file: {e}")

    def _save_stats(self):
        """Save stats to file"""
        try:
            data = {
                'session': asdict(self.session),
                'products': {asin: asdict(prod) for asin, prod in self.products.items()},
                'activity_history': self.activity_history[-1000:]
            }

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save stats file: {e}")

    def initialize_session(self, queries: List[str]):
        """
        Initialize a new scrape session.

        Args:
            queries: List of search queries to run
        """
        self.session = SessionStats()
        self.session.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.session.queries_run = 0
        self.start_time = time.time()
        self._save_stats()

    def start_query(self, query: str):
        """Mark start of a search query scrape"""
        self.session.current_query = query
        self.session.queries_run += 1
        self.log_activity('QUERY', query, f'Starting scrape for: {query}')
        self._save_stats()

    def register_product(self, asin: str, title: str = ''):
        """Register a product for tracking"""
        if asin not in self.products:
            self.products[asin] = ProductStats(
                asin=asin,
                title=title,
                first_seen=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            self.session.products_total += 1
            self._save_stats()

    def log_scrape(self, asin: str, price: str = '', seller: str = '', success: bool = True):
        """
        Log a product scrape result.

        Args:
            asin: Product ASIN
            price: Scraped price
            seller: Default seller name
            success: Whether scrape was successful
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if asin in self.products:
            prod = self.products[asin]
            prod.last_scraped = timestamp
            prod.scrape_count += 1

            if success:
                prod.status = 'scraped'
                if price:
                    prod.current_price = price
                    prod.sellers_seen += 1

                    # Track price range
                    try:
                        price_val = float(price.replace(',', ''))
                        if not prod.lowest_price or prod.lowest_price == '0':
                            prod.lowest_price = price
                            prod.highest_price = price
                        else:
                            low_val = float(prod.lowest_price.replace(',', ''))
                            high_val = float(prod.highest_price.replace(',', ''))
                            if price_val < low_val:
                                prod.lowest_price = price
                            if price_val > high_val:
                                prod.highest_price = price

                            # Track price changes
                            if price_val != low_val:
                                prod.price_changes += 1
                                self.session.total_price_changes += 1
                    except (ValueError, AttributeError):
                        pass

                self.session.products_scraped += 1
                self.log_activity('SCRAPE', asin, f'Success: ₹{price}', 'OK')
            else:
                prod.status = 'error'
                prod.errors += 1
                self.session.products_failed += 1
                self.session.total_errors += 1
                self.log_activity('SCRAPE', asin, 'Failed', 'FAILED')

        self._save_stats()

    def log_analysis(self, asin: str, recommendation: str = ''):
        """Log an AI analysis run"""
        self.session.analyses_run += 1
        self.log_activity('ANALYSIS', asin, recommendation[:80] if recommendation else 'Completed', 'OK')
        self._save_stats()

    def log_error(self, asin: str, error: str, context: str = ''):
        """Log an error"""
        self.session.total_errors += 1
        self.log_activity('ERROR', asin, error, f'FAILED - {context}')
        self._save_stats()

    def log_activity(self, activity_type: str, identifier: str, details: str = ''):
        """
        Log a generic activity.

        Args:
            activity_type: Type (QUERY, SCRAPE, ANALYSIS, ERROR, etc.)
            identifier: ASIN or query string
            details: Activity details
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        activity = {
            'timestamp': timestamp,
            'identifier': identifier,
            'type': activity_type,
            'details': details
        }

        self.activity_history.append(activity)
        self._save_stats()

    def get_session_summary(self) -> Dict:
        """Get session summary"""
        elapsed = time.time() - self.start_time

        return {
            'session_start': self.session.start_time,
            'elapsed_time': self._format_duration(elapsed),
            'queries': {
                'run': self.session.queries_run,
            },
            'products': {
                'total': self.session.products_total,
                'scraped': self.session.products_scraped,
                'failed': self.session.products_failed,
            },
            'activities': {
                'sellers_found': self.session.total_sellers_found,
                'price_changes': self.session.total_price_changes,
                'analyses': self.session.analyses_run,
                'errors': self.session.total_errors
            },
            'current_query': self.session.current_query
        }

    def _format_duration(self, seconds: float) -> str:
        """Format seconds as human-readable duration"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def get_recent_activities(self, limit: int = 20) -> List[Dict]:
        """Get recent activities"""
        return self.activity_history[-limit:]

    def get_progress_percentage(self) -> float:
        """Get overall progress percentage"""
        if self.session.products_total == 0:
            return 0.0
        completed = self.session.products_scraped
        return (completed / self.session.products_total) * 100 if self.session.products_total > 0 else 0

    def get_price_alerts(self) -> List[Dict]:
        """Get products with recent price changes"""
        alerts = []
        for asin, prod in self.products.items():
            if prod.price_changes > 0 and prod.last_scraped:
                alerts.append({
                    'asin': asin,
                    'title': prod.title,
                    'current_price': prod.current_price,
                    'lowest_price': prod.lowest_price,
                    'highest_price': prod.highest_price,
                    'changes': prod.price_changes,
                    'last_updated': prod.last_scraped
                })
        return sorted(alerts, key=lambda x: x['changes'], reverse=True)

    def export_report(self, filename: str = 'monitor_report.txt'):
        """Export a text report of all statistics"""
        summary = self.get_session_summary()

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("     AMAZON PRICE MONITOR - SESSION REPORT\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Session Started: {summary['session_start']}\n")
            f.write(f"Elapsed Time: {summary['elapsed_time']}\n")
            f.write(f"Current Query: {summary['current_query']}\n\n")

            f.write("-" * 60 + "\n")
            f.write("PRODUCT STATUS\n")
            f.write("-" * 60 + "\n")

            for asin, prod in self.products.items():
                f.write(f"\n{asin}:\n")
                f.write(f"  Title: {prod.title}\n")
                f.write(f"  Status: {prod.status}\n")
                f.write(f"  Current Price: ₹{prod.current_price}\n")
                f.write(f"  Lowest Price: ₹{prod.lowest_price}\n")
                f.write(f"  Highest Price: ₹{prod.highest_price}\n")
                f.write(f"  Price Changes: {prod.price_changes}\n")
                f.write(f"  Scrape Count: {prod.scrape_count}\n")
                f.write(f"  Last Scraped: {prod.last_scraped}\n")

            f.write("\n" + "-" * 60 + "\n")
            f.write("SUMMARY\n")
            f.write("-" * 60 + "\n")
            f.write(f"Queries Run: {summary['queries']['run']}\n")
            f.write(f"Products Scraped: {summary['products']['scraped']}\n")
            f.write(f"Products Failed: {summary['products']['failed']}\n")
            f.write(f"Price Changes Detected: {summary['activities']['price_changes']}\n")
            f.write(f"Analyses Run: {summary['activities']['analyses']}\n")
            f.write(f"Total Errors: {summary['activities']['errors']}\n")
            f.write(f"Progress: {self.get_progress_percentage():.1f}%\n")

            # Price alerts
            alerts = self.get_price_alerts()
            if alerts:
                f.write("\n" + "-" * 60 + "\n")
                f.write("PRICE CHANGE ALERTS\n")
                f.write("-" * 60 + "\n")
                for alert in alerts:
                    f.write(f"\n{alert['asin']} ({alert['title'][:40]}):\n")
                    f.write(f"  Current: ₹{alert['current_price']} | "
                           f"Low: ₹{alert['lowest_price']} | "
                           f"High: ₹{alert['highest_price']}\n")
                    f.write(f"  Changes detected: {alert['changes']}\n")


# Global stats tracker instance
stats_tracker = StatsTracker()
