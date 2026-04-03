"""
Enhanced Logger for Amazon Price Monitor - Colored console output + file logging.
Tracks scrape sessions, product checks, analysis runs, and errors.
"""
import logging
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path


class ColorFormatter(logging.Formatter):
    """Custom formatter with colored output for console"""

    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'SCRAPE': '\033[36m',
        'ANALYSIS': '\033[35m',
        'SUCCESS': '\033[92m',
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"

        if hasattr(record, 'scrape'):
            record.msg = f"{self.COLORS['SCRAPE']}[SCRAPE]{self.COLORS['RESET']} {record.msg}"
        if hasattr(record, 'analysis'):
            record.msg = f"{self.COLORS['ANALYSIS']}[ANALYSIS]{self.COLORS['RESET']} {record.msg}"
        if hasattr(record, 'success') and record.success:
            record.msg = f"{self.COLORS['SUCCESS']}✓ {record.msg}{self.COLORS['RESET']}"

        return super().format(record)


def setup_logger(
    name: str = 'amazon_monitor',
    log_file: str = 'amazon_scraper.log',
    level: str = 'INFO',
    detailed: bool = True
) -> logging.Logger:
    """
    Set up logger with console and file handlers.

    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        detailed: Include detailed formatting

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers = []

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))

    if detailed:
        console_format = ColorFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        console_format = logging.Formatter('%(message)s')

    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (plain text)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger


def log_scrape_start(logger: logging.Logger, query: str, asin_count: int = 0):
    """Log the start of a scrape session"""
    extra = {'scrape': True}
    msg = f"Starting scrape for query: '{query}'"
    if asin_count:
        msg += f" ({asin_count} ASINs found)"
    logger.info(msg, extra=extra)


def log_product_scraped(logger: logging.Logger, asin: str, title: str, price: str):
    """Log a successfully scraped product"""
    extra = {'scrape': True, 'success': True}
    logger.info(f"Scraped ASIN {asin}: {title[:50]} - ₹{price}", extra=extra)


def log_analysis_run(logger: logging.Logger, asin: str):
    """Log an AI analysis run"""
    extra = {'analysis': True}
    logger.info(f"Running AI analysis for ASIN: {asin}", extra=extra)


def log_success(logger: logging.Logger, message: str):
    """Log a successful action"""
    extra = {'success': True}
    logger.info(message, extra=extra)


def log_error(logger: logging.Logger, message: str, exc_info: bool = False):
    """Log an error"""
    logger.error(f"✗ {message}", exc_info=exc_info)


class ActivityLogger:
    """
    Specialized logger for tracking monitoring activities with timestamps.
    Writes to a separate activity log for easy monitoring.
    """

    def __init__(self, log_file: str = 'activity.log'):
        self.log_file = Path(log_file)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create log file if it doesn't exist"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.touch()

    def _timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def log(self, category: str, asin: str, action: str, details: str = '', status: str = 'OK'):
        """
        Log an activity.

        Args:
            category: Activity category (SCRAPE, ANALYSIS, SCHEDULE, ERROR)
            asin: Product ASIN (or query string)
            action: Action performed
            details: Additional details
            status: Status (OK, SUCCESS, FAILED, SKIPPED)
        """
        timestamp = self._timestamp()
        log_line = f"[{timestamp}] [{status:8}] [{category:12}] [{asin:15}] {action}"
        if details:
            log_line += f" - {details}"

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')

    def log_scrape(self, query: str, asin: str, price: str = '', seller: str = ''):
        """Log a product scrape"""
        details = f'Price: ₹{price}' if price else ''
        if seller:
            details += f' | Seller: {seller}'
        self.log('SCRAPE', asin, f'Scraped via query: {query}', details, 'SUCCESS')

    def log_analysis(self, asin: str, recommendation: str = ''):
        """Log an AI analysis"""
        self.log('ANALYSIS', asin, 'AI analysis completed', recommendation[:100], 'OK')

    def log_session_start(self, query: str):
        """Log a scrape session start"""
        self.log('SCHEDULE', query, 'Scrape session started', '', 'OK')

    def log_session_end(self, query: str, products_count: int):
        """Log a scrape session end"""
        self.log('SCHEDULE', query, f'Session complete', f'{products_count} products scraped', 'OK')

    def log_error(self, asin: str, error: str, context: str = ''):
        """Log an error"""
        self.log('ERROR', asin, error, context, 'FAILED')

    def log_blocked(self, url: str, status_code: int):
        """Log a blocking event (403/429)"""
        self.log('BLOCKED', url[:30], f'HTTP {status_code}', 'Rotating proxy/retrying', 'FAILED')

    def log_proxy_rotation(self):
        """Log a proxy rotation"""
        self.log('PROXY', '-', 'Proxy rotated', '', 'SUCCESS')

    def get_recent_activities(self, limit: int = 50) -> list:
        """
        Get recent activities from log.

        Args:
            limit: Number of recent entries to return

        Returns:
            List of recent log entries
        """
        if not self.log_file.exists():
            return []

        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        return lines[-limit:]

    def clear(self):
        """Clear the activity log"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('')


# Global activity logger instance
activity_logger = ActivityLogger()
