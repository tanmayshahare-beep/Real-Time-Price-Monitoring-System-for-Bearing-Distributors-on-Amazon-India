#!/usr/bin/env python
"""
CLI for Amazon Price Monitor - Arrow-key navigable interface.
Uses raw keyboard input for smooth navigation with ↑↓ arrows and Enter.

Usage:
    python cli.py              Open interactive menu (default)
"""
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from human_behavior import HumanTiming
from stats import stats_tracker
from logger import activity_logger
from log_viewer import LogViewer


# ==================== Colors ====================

class C:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


# ==================== Keyboard Input ====================

class KeyInput:
    """Cross-platform raw keyboard input"""

    KEY_UP = 'UP'
    KEY_DOWN = 'DOWN'
    KEY_ENTER = 'ENTER'
    KEY_ESC = 'ESC'
    KEY_BACKSPACE = 'BACKSPACE'
    KEY_SPACE = 'SPACE'

    @staticmethod
    def get_key():
        """
        Get a single keypress. Returns:
        'UP', 'DOWN', 'ENTER', 'ESC', 'BACKSPACE', 'SPACE', or the character typed.
        """
        if os.name == 'nt':
            return KeyInput._get_key_windows()
        else:
            return KeyInput._get_key_unix()

    @staticmethod
    def _get_key_windows():
        import msvcrt
        ch = msvcrt.getch()

        # Arrow keys send as two bytes: 0xE0 or 0x00 + scan code
        if ch in (b'\xe0', b'\x00'):
            ch2 = msvcrt.getch()
            if ch2 == b'H': return KeyInput.KEY_UP
            if ch2 == b'P': return KeyInput.KEY_DOWN
            if ch2 == b'K': return KeyInput.KEY_LEFT
            if ch2 == b'M': return KeyInput.KEY_RIGHT
            return None

        if ch == b'\r' or ch == b'\n':
            return KeyInput.KEY_ENTER
        if ch == b'\x1b':
            return KeyInput.KEY_ESC
        if ch == b'\x08' or ch == b'\x7f':
            return KeyInput.KEY_BACKSPACE
        if ch == b' ':
            return KeyInput.KEY_SPACE

        try:
            return ch.decode('utf-8', errors='ignore')
        except Exception:
            return None

    @staticmethod
    def _get_key_unix():
        import tty
        import termios
        import select

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            # Check if data is available
            if not select.select([sys.stdin], [], [], 0.1)[0]:
                return None

            ch = sys.stdin.read(1)

            if ch == '\x1b':
                # Could be arrow key escape sequence
                if select.select([sys.stdin], [], [], 0.01)[0]:
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        if select.select([sys.stdin], [], [], 0.01)[0]:
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'A': return KeyInput.KEY_UP
                            if ch3 == 'B': return KeyInput.KEY_DOWN
                            if ch3 == 'C': return KeyInput.KEY_RIGHT
                            if ch3 == 'D': return KeyInput.KEY_LEFT
                return KeyInput.KEY_ESC

            if ch == '\r' or ch == '\n':
                return KeyInput.KEY_ENTER
            if ch == '\x7f' or ch == '\x08':
                return KeyInput.KEY_BACKSPACE
            if ch == ' ':
                return KeyInput.KEY_SPACE
            return ch
        except Exception:
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ==================== Menu System ====================

class MenuItem:
    """A single menu item"""
    def __init__(self, label, action=None, color=None, dim=False, separator=False):
        self.label = label
        self.action = action  # None = section header or separator
        self.color = color
        self.dim = dim
        self.separator = separator

    def render(self, selected, cursor_char):
        if self.separator:
            return f"  {self.label}"

        if self.action is not None:
            # Selectable item
            if selected:
                bg = '\033[44m'  # Blue background
                return f"{cursor_char} {bg}{C.BOLD} {self.label} {C.RESET}"
            else:
                prefix = f"  {cursor_char} "
                color = self.color if self.color else C.WHITE
                return f"{prefix}{color}{self.label}{C.RESET}"
        else:
            # Section header
            color = self.color if self.color else C.WHITE
            if self.dim:
                return f"  {cursor_char} {C.DIM}{self.label}{C.RESET}"
            return f"  {cursor_char} {C.BOLD}{color}{self.label}{C.RESET}"


def render_menu(title, items, selected_index, cursor_char="▸"):
    """Render a complete menu with cursor highlighting"""
    clear()

    # Title
    print(f"{C.BRIGHT_CYAN}{'═'*60}{C.RESET}")
    print(f"{C.BOLD}     {title}{C.RESET}")
    now = datetime.now().strftime('%A, %d %B %Y  •  %H:%M:%S')
    print(f"{C.DIM}     {now}{C.RESET}")
    print(f"{C.BRIGHT_CYAN}{'═'*60}{C.RESET}")
    print()

    # Items
    for i, item in enumerate(items):
        print(item.render(i == selected_index, cursor_char))

    print()
    print(f"  {C.DIM}↑↓ navigate  •  Enter select  •  Esc back{C.RESET}")


def run_menu(title, items):
    """
    Run a navigable menu. Returns the action of the selected item, or None if escaped.

    Args:
        title: Menu title string
        items: List of MenuItem objects

    Returns:
        The action value of the selected item, or None
    """
    selected = 0

    # Find first selectable item
    selectable = [i for i, item in enumerate(items) if item.action is not None and not item.separator]
    if selectable:
        selected = selectable[0]

    while True:
        render_menu(title, items, selected)

        key = KeyInput.get_key()

        if key == KeyInput.KEY_UP:
            # Move to previous selectable item
            idx = selectable.index(selected) if selected in selectable else -1
            if idx > 0:
                selected = selectable[idx - 1]
            else:
                selected = selectable[-1]

        elif key == KeyInput.KEY_DOWN:
            # Move to next selectable item
            idx = selectable.index(selected) if selected in selectable else -1
            if idx < len(selectable) - 1:
                selected = selectable[idx + 1]
            else:
                selected = selectable[0]

        elif key == KeyInput.KEY_ENTER:
            return items[selected].action

        elif key == KeyInput.KEY_ESC:
            return None


# ==================== Header & Status ====================

def draw_status_strip():
    config = Config()
    tracker = stats_tracker
    summary = tracker.get_session_summary()

    items = []
    if summary.get('session_start'):
        items.append(f"Session: {C.BRIGHT_GREEN}active{C.RESET}")
        items.append(f"Products: {C.CYAN}{summary['products']['scraped']}{C.RESET}")
        if summary['activities']['price_changes'] > 0:
            items.append(f"Price changes: {C.BRIGHT_YELLOW}{summary['activities']['price_changes']}{C.RESET}")
        if summary['activities']['errors'] > 0:
            items.append(f"Errors: {C.BRIGHT_RED}{summary['activities']['errors']}{C.RESET}")
    else:
        items.append(f"Session: {C.DIM}none{C.RESET}")

    items.append(f"Queries: {len(config.TARGET_QUERIES)}")
    if config.MONITORED_ASINS:
        items.append(f"ASINs: {len(config.MONITORED_ASINS)}")

    print(f"  {' | '.join(items)}")
    print()


# ==================== Screen: Main Menu ====================

def build_main_menu_items():
    items = []

    # Scraping
    items.append(MenuItem("SCRAPING", color=C.BRIGHT_CYAN))
    items.append(MenuItem("Run Scrape (default query)", action="scrape_default"))
    items.append(MenuItem("Run Scrape (custom query)", action="scrape_custom"))
    items.append(MenuItem("Run Scrape with decoy queries", action="scrape_decoy"))
    items.append(MenuItem("Start Continuous Monitoring", action="monitor"))

    items.append(MenuItem("", separator=True))

    # Analysis
    items.append(MenuItem("ANALYSIS", color=C.BRIGHT_MAGENTA))
    items.append(MenuItem("Run AI Price Analysis", action="analyze"))

    items.append(MenuItem("", separator=True))

    # Status & Reports
    items.append(MenuItem("STATUS & REPORTS", color=C.BRIGHT_GREEN))
    items.append(MenuItem("View Session Status", action="status"))
    items.append(MenuItem("View Price Alerts", action="price_alerts"))
    items.append(MenuItem("Export Session Report", action="report"))

    items.append(MenuItem("", separator=True))

    # Logs
    items.append(MenuItem("LOGS", color=C.BRIGHT_YELLOW))
    items.append(MenuItem("View Activity Log", action="activity_log"))
    items.append(MenuItem("View Errors Only", action="errors"))
    items.append(MenuItem("Search Logs", action="search_logs"))
    items.append(MenuItem("View Scraper Log", action="scraper_log"))

    items.append(MenuItem("", separator=True))

    # Configuration
    items.append(MenuItem("CONFIGURATION", color=C.BRIGHT_BLUE))
    items.append(MenuItem("Show Configuration", action="config_show"))
    items.append(MenuItem("Manage Queries & ASINs", action="manage_queries"))
    items.append(MenuItem("Change Scrape Interval", action="change_interval"))

    items.append(MenuItem("", separator=True))

    # Control
    running = _count_running_processes()
    items.append(MenuItem("CONTROL", color=C.BRIGHT_RED))
    if running > 0:
        items.append(MenuItem(f"Kill Switch ({running} process(es) running)",
                              action="killswitch", color=C.BRIGHT_RED))
    else:
        items.append(MenuItem("Kill Switch (all clear)", action="killswitch"))

    items.append(MenuItem("", separator=True))
    items.append(MenuItem("Exit", action="exit"))

    return items


def show_main_menu():
    while True:
        clear()
        print(f"{C.BRIGHT_CYAN}{'═'*60}{C.RESET}")
        print(f"{C.BOLD}     Amazon Price Monitor - Control Panel{C.RESET}")
        print(f"{C.DIM}     Real-Time Price Monitoring for Amazon India{C.RESET}")
        now = datetime.now().strftime('%A, %d %B %Y  •  %H:%M:%S')
        print(f"{C.DIM}     {now}{C.RESET}")
        print(f"{C.BRIGHT_CYAN}{'═'*60}{C.RESET}")
        print()
        draw_status_strip()

        items = build_main_menu_items()
        action = run_menu("Amazon Price Monitor - Control Panel", items)

        if action == "exit":
            clear()
            print(f"\n  {C.DIM}Goodbye! 👋{C.RESET}\n")
            break
        elif action == "scrape_default":
            screen_scrape()
        elif action == "scrape_custom":
            screen_scrape_custom()
        elif action == "scrape_decoy":
            screen_scrape_with_decoy()
        elif action == "monitor":
            screen_monitor()
        elif action == "analyze":
            screen_analyze()
        elif action == "status":
            screen_status()
        elif action == "price_alerts":
            screen_price_alerts()
        elif action == "report":
            screen_report()
        elif action == "activity_log":
            screen_activity_log()
        elif action == "errors":
            screen_errors()
        elif action == "search_logs":
            screen_search_logs()
        elif action == "scraper_log":
            screen_scraper_log()
        elif action == "config_show":
            screen_config()
        elif action == "manage_queries":
            screen_manage_queries()
        elif action == "change_interval":
            screen_change_interval()
        elif action == "killswitch":
            screen_killswitch()


# ==================== Screen: Scrape ====================

def screen_scrape():
    config = Config()
    if not config.TARGET_QUERIES:
        clear()
        print(f"\n  {C.BRIGHT_RED}No target queries configured.{C.RESET}")
        wait()
        return

    run_scrape(config.TARGET_QUERIES[0], decoy=False)


def screen_scrape_custom():
    clear()
    print(f"{C.BOLD}{'Custom Scrape':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")
    query = input_text("  Enter search query: ")
    if not query:
        return
    run_scrape(query, decoy=False)


def screen_scrape_with_decoy():
    config = Config()
    if not config.TARGET_QUERIES:
        clear()
        print(f"\n  {C.BRIGHT_RED}No target queries configured.{C.RESET}")
        wait()
        return

    run_scrape(config.TARGET_QUERIES[0], decoy=True)


def run_scrape(query, decoy=False):
    clear()
    print(f"{C.BOLD}{'Scrape Session':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print(f"  Target query : {C.BRIGHT_GREEN}{query}{C.RESET}")
    print(f"  Decoy queries: {C.YELLOW}{'yes' if decoy else 'no'}{C.RESET}")
    print(f"  Human timing : {C.BRIGHT_GREEN}enabled{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")

    activity_logger.log_session_start(query)
    stats_tracker.initialize_session([query])

    config = Config()
    timing = HumanTiming()

    if decoy and config.DECOY_QUERIES:
        decoy_query = config.get_random_decoy_query()
        print(f"  {C.DIM}[decoy]{C.RESET} Scraping: {C.CYAN}{decoy_query}{C.RESET}")
        _run_scrapy(decoy_query)
        print(f"  {C.DIM}Delaying (human-like pause)...{C.RESET}\n")
        timing.between_searches()

    print(f"  {C.BOLD}[target]{C.RESET} Scraping: {C.BRIGHT_GREEN}{query}{C.RESET}")
    start = time.time()
    products = _run_scrapy(query)
    elapsed = time.time() - start

    print()
    if products > 0:
        print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Scraped {C.BOLD}{products}{C.RESET} product(s) in {C.CYAN}{format_duration(elapsed)}{C.RESET}")
        activity_logger.log_session_end(query, products)
    else:
        print(f"  {C.BRIGHT_RED}✗{C.RESET} No products scraped")
        activity_logger.log_error(query, 'No products scraped', 'Scrape')

    print(f"\n{C.DIM}{'─'*60}{C.RESET}")
    wait()


def _run_scrapy(query):
    try:
        result = subprocess.run(
            ['scrapy', 'crawl', 'amazon', '-a', f'query={query}'],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            count = sum(1 for line in result.stdout.split('\n') if 'Scraped ASIN' in line)
            return max(count, 1)
        return 0
    except subprocess.TimeoutExpired:
        return 0
    except Exception:
        return 0


# ==================== Screen: Monitor ====================

def screen_monitor():
    config = Config()
    clear()
    print(f"{C.BOLD}{'Continuous Monitoring':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print(f"  Interval     : {C.BRIGHT_CYAN}{config.SCRAPE_INTERVAL_HOURS}h{C.RESET} (±{config.SCHEDULE_JITTER_MINUTES}m jitter)")
    print(f"  Target queries: {C.BRIGHT_GREEN}{', '.join(config.TARGET_QUERIES)}{C.RESET}")
    if config.DECOY_QUERIES:
        print(f"  Decoy queries : {C.YELLOW}{', '.join(config.DECOY_QUERIES)}{C.RESET}")
    print(f"  Human timing  : {C.BRIGHT_GREEN}enabled{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print()

    items = [
        MenuItem("Start monitoring now", action="start"),
        MenuItem("Cancel", action="cancel"),
    ]
    action = run_menu("Continuous Monitoring", items)

    if action != "start":
        return

    print(f"\n  {C.DIM}Press Ctrl+C to stop monitoring{C.RESET}\n")
    try:
        from orchestrator import AmazonMonitorOrchestrator
        monitor = AmazonMonitorOrchestrator(config)
        monitor.run_scheduled_monitoring()
    except KeyboardInterrupt:
        print(f"\n  {C.YELLOW}Monitoring stopped{C.RESET}")
        wait()


# ==================== Screen: Analysis ====================

def screen_analyze():
    config = Config()
    items = []
    all_asins = []

    if stats_tracker.products:
        for asin, prod in stats_tracker.products.items():
            items.append(MenuItem(f"{asin}  (last: ₹{prod.current_price})", action=asin))
            all_asins.append(asin)

    if config.MONITORED_ASINS:
        for asin in config.MONITORED_ASINS:
            if asin not in all_asins:
                items.append(MenuItem(f"{asin}  (monitored)", action=asin))
                all_asins.append(asin)

    items.append(MenuItem("Enter custom ASIN", action="__custom__"))
    items.append(MenuItem("Cancel", action=None))

    action = run_menu("AI Price Analysis", items)

    if action is None:
        return

    if action == "__custom__":
        asin = input_text("  Enter ASIN: ")
        if not asin:
            return
    else:
        asin = action

    print(f"\n  {C.DIM}Running analysis for {asin}...{C.RESET}\n")
    activity_logger.log_session_start(f"analysis-{asin}")

    try:
        result = subprocess.run(
            ['python', '-m', 'analysis.analyze', asin],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if 'trend' in line.lower() or 'stable' in line.lower():
                    print(f"  {C.BRIGHT_CYAN}{line}{C.RESET}")
                elif 'price' in line.lower() or '₹' in line:
                    print(f"  {C.BRIGHT_GREEN}{line}{C.RESET}")
                elif 'recommend' in line.lower():
                    print(f"  {C.BRIGHT_YELLOW}{line}{C.RESET}")
                else:
                    print(f"  {C.WHITE}{line}{C.RESET}")
            activity_logger.log_analysis(asin, result.stdout[:200])
            stats_tracker.log_analysis(asin, result.stdout)
        else:
            print(f"  {C.BRIGHT_RED}✗ Analysis failed: {result.stderr[:300]}{C.RESET}")
    except subprocess.TimeoutExpired:
        print(f"  {C.BRIGHT_RED}✗ Timed out (120s){C.RESET}")
    except FileNotFoundError:
        print(f"  {C.BRIGHT_RED}✗ Ollama not running{C.RESET}")
    except Exception as e:
        print(f"  {C.BRIGHT_RED}✗ Error: {e}{C.RESET}")

    wait()


# ==================== Screen: Status ====================

def screen_status():
    clear()
    tracker = stats_tracker
    summary = tracker.get_session_summary()

    lines = []
    lines.append(f"{C.BOLD}Session Status{C.RESET}")
    lines.append("")

    if not summary.get('session_start'):
        lines.append(f"  {C.YELLOW}No active session. Run a scrape first.{C.RESET}")
    else:
        lines.append(f"  Session started : {C.BRIGHT_CYAN}{summary['session_start']}{C.RESET}")
        lines.append(f"  Elapsed time    : {C.CYAN}{summary['elapsed_time']}{C.RESET}")
        lines.append(f"  Queries run     : {C.BOLD}{summary['queries']['run']}{C.RESET}")
        lines.append("")
        lines.append(f"  Products scraped : {C.BRIGHT_GREEN}{summary['products']['scraped']}{C.RESET}")
        lines.append(f"  Products failed  : {C.BRIGHT_RED}{summary['products']['failed']}{C.RESET}")
        lines.append(f"  Price changes    : {C.BRIGHT_YELLOW}{summary['activities']['price_changes']}{C.RESET}")
        lines.append(f"  Analyses run     : {C.BRIGHT_MAGENTA}{summary['activities']['analyses']}{C.RESET}")
        lines.append(f"  Errors           : {C.BRIGHT_RED}{summary['activities']['errors']}{C.RESET}")

        if tracker.products:
            lines.append("")
            lines.append(f"  {C.BOLD}Products{C.RESET}")
            lines.append(f"  {'─'*58}")
            lines.append(f"  {'ASIN':<15} {'Price':<10} {'Low':<10} {'High':<10} {'Changes':<8} {'Status'}")
            lines.append(f"  {'─'*58}")
            for asin, prod in tracker.products.items():
                sc = C.GREEN if prod.status == 'scraped' else C.RED if prod.status == 'error' else C.YELLOW
                lines.append(f"  {C.CYAN}{asin:<15}{C.RESET} {C.GREEN}₹{prod.current_price:<9}{C.RESET} {C.GREEN}₹{prod.lowest_price:<9}{C.RESET} {C.YELLOW}₹{prod.highest_price:<9}{C.RESET} {prod.price_changes:<8} {sc}{prod.status}{C.RESET}")

            progress = tracker.get_progress_percentage()
            bar_len = 40
            filled = int(bar_len * progress / 100) if tracker.session.products_total else 0
            bar = f"{C.GREEN}{'█'*filled}{C.RESET}{'░'*(bar_len-filled)}"
            lines.append("")
            lines.append(f"  Progress: [{bar}] {progress:.1f}%")

    lines.append("")
    lines.append(f"  {C.DIM}Press any key to go back{C.RESET}")

    _show_text_lines(lines)


# ==================== Screen: Price Alerts ====================

def screen_price_alerts():
    clear()
    alerts = stats_tracker.get_price_alerts()

    lines = []
    lines.append(f"{C.BOLD}Price Change Alerts{C.RESET}")
    lines.append("")

    if not alerts:
        lines.append(f"  {C.YELLOW}No price changes detected yet.{C.RESET}")
    else:
        for a in alerts:
            lines.append(f"  {C.BOLD}●{C.RESET} {C.CYAN}{a['asin']}{C.RESET}")
            lines.append(f"     Title   : {a['title'][:50]}")
            lines.append(f"     Current : {C.GREEN}₹{a['current_price']}{C.RESET}")
            lines.append(f"     Range   : {C.GREEN}₹{a['lowest_price']}{C.RESET} - {C.YELLOW}₹{a['highest_price']}{C.RESET}")
            lines.append(f"     Changes : {C.BOLD}{a['changes']}{C.RESET}")
            lines.append(f"     Updated : {a['last_updated']}")
            lines.append("")

    lines.append(f"  {C.DIM}Press any key to go back{C.RESET}")
    _show_text_lines(lines)


# ==================== Screen: Report ====================

def screen_report():
    clear()
    tracker = stats_tracker

    if not tracker.products and not tracker.session.start_time:
        print(f"\n  {C.YELLOW}No data to report. Run a scrape first.{C.RESET}")
        wait()
        return

    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    tracker.export_report(filename)

    summary = tracker.get_session_summary()
    lines = []
    lines.append(f"{C.BOLD}Session Report Exported{C.RESET}")
    lines.append("")
    lines.append(f"  Session  : {C.BRIGHT_CYAN}{summary['session_start']}{C.RESET}")
    lines.append(f"  Elapsed  : {C.CYAN}{summary['elapsed_time']}{C.RESET}")
    lines.append(f"  Scraped  : {C.BRIGHT_GREEN}{summary['products']['scraped']}{C.RESET}")
    lines.append(f"  Failed   : {C.BRIGHT_RED}{summary['products']['failed']}{C.RESET}")
    lines.append(f"  Changes  : {C.BRIGHT_YELLOW}{summary['activities']['price_changes']}{C.RESET}")
    lines.append(f"  Errors   : {C.BRIGHT_RED}{summary['activities']['errors']}{C.RESET}")
    lines.append("")
    lines.append(f"  {C.BRIGHT_GREEN}✓{C.RESET} Saved to {C.BOLD}{filename}{C.RESET}")
    lines.append("")
    lines.append(f"  {C.DIM}Press any key to go back{C.RESET}")
    _show_text_lines(lines)


# ==================== Screen: Logs ====================

def screen_activity_log():
    types = ['ALL', 'SCRAPE', 'ANALYSIS', 'SCHEDULE', 'ERROR', 'BLOCKED', 'PROXY']
    items = [MenuItem(t, action=t) for t in types]
    items.append(MenuItem("Cancel", action=None))

    action = run_menu("Activity Log — Select Filter", items)
    if action is None or action == 'ALL':
        filter_type = None
    else:
        filter_type = action

    viewer = LogViewer()
    viewer.view_activity_log(50, filter_type)
    wait()


def screen_errors():
    viewer = LogViewer()
    viewer.view_errors()
    wait()


def screen_search_logs():
    clear()
    query = input_text("  Search logs for: ")
    if not query:
        return
    viewer = LogViewer()
    viewer.search(query)
    wait()


def screen_scraper_log():
    viewer = LogViewer()
    viewer.view_bot_log()
    wait()


# ==================== Screen: Config ====================

def screen_config():
    config = Config()
    lines = []
    lines.append(f"{C.BOLD}Configuration{C.RESET}")
    lines.append("")

    sections = [
        ('Amazon', [
            ('Domain', config.AMAZON_DOMAIN),
            ('Target queries', ', '.join(config.TARGET_QUERIES)),
            ('Decoy queries', ', '.join(config.DECOY_QUERIES) if config.DECOY_QUERIES else '(none)'),
            ('Monitored ASINs', ', '.join(config.MONITORED_ASINS) if config.MONITORED_ASINS else '(none)'),
        ]),
        ('Scheduling', [
            ('Interval', f"{config.SCRAPE_INTERVAL_HOURS}h"),
            ('Jitter', f"±{config.SCHEDULE_JITTER_MINUTES}m"),
        ]),
        ('Behavioral', [
            ('Request delay', f"{config.REQUEST_DELAY_MIN}-{config.REQUEST_DELAY_MAX}s"),
            ('Product read', f"{config.READING_TIME_PRODUCT_MIN}-{config.READING_TIME_PRODUCT_MAX}s"),
            ('Hesitation', config.HESITATION_PROBABILITY),
        ]),
        ('Infrastructure', [
            ('MongoDB', config.MONGO_URI),
            ('Proxies', len(config.PROXY_LIST)),
            ('Ollama', config.OLLAMA_MODEL),
        ]),
    ]

    for section, items_list in sections:
        lines.append(f"  {C.BOLD}{C.BRIGHT_CYAN}{section}{C.RESET}")
        lines.append(f"  {'─'*50}")
        for key, val in items_list:
            lines.append(f"  {C.DIM}{key:<22}{C.RESET} {val}")
        lines.append("")

    lines.append(f"  {C.DIM}Press any key to go back{C.RESET}")
    _show_text_lines(lines)


# ==================== Screen: Manage Queries ====================

def screen_manage_queries():
    config = Config()
    while True:
        items = []

        if config.TARGET_QUERIES:
            items.append(MenuItem("TARGET QUERIES", color=C.GREEN))
            for q in config.TARGET_QUERIES:
                items.append(MenuItem(f"  {q}", action=None, dim=True))
            items.append(MenuItem("", separator=True))

        if config.DECOY_QUERIES:
            items.append(MenuItem("DECOY QUERIES", color=C.YELLOW))
            for q in config.DECOY_QUERIES:
                items.append(MenuItem(f"  {q}", action=None, dim=True))
            items.append(MenuItem("", separator=True))

        if config.MONITORED_ASINS:
            items.append(MenuItem("MONITORED ASINS", color=C.CYAN))
            for a in config.MONITORED_ASINS:
                items.append(MenuItem(f"  {a}", action=None, dim=True))
            items.append(MenuItem("", separator=True))

        items.append(MenuItem("Add target query", action="add_target"))
        items.append(MenuItem("Add decoy query", action="add_decoy"))
        items.append(MenuItem("Add monitored ASIN", action="add_asin"))
        items.append(MenuItem("Remove target query", action="remove_target"))
        items.append(MenuItem("Remove decoy query", action="remove_decoy"))
        items.append(MenuItem("Remove monitored ASIN", action="remove_asin"))
        items.append(MenuItem("Back", action="back"))

        action = run_menu("Manage Queries & ASINs", items)

        if action in ("back", None):
            break
        elif action == "add_target":
            val = input_text("  Query to add: ")
            if val:
                _env_edit('TARGET_QUERIES', val)
                config = Config()
        elif action == "add_decoy":
            val = input_text("  Decoy query to add: ")
            if val:
                _env_edit('DECOY_QUERIES', val)
                config = Config()
        elif action == "add_asin":
            val = input_text("  ASIN to add: ")
            if val:
                _env_edit('MONITORED_ASINS', val)
                config = Config()
        elif action == "remove_target":
            _remove_from_list('TARGET_QUERIES', 'Target Queries', config)
            config = Config()
        elif action == "remove_decoy":
            _remove_from_list('DECOY_QUERIES', 'Decoy Queries', config)
            config = Config()
        elif action == "remove_asin":
            _remove_from_list('MONITORED_ASINS', 'Monitored ASINs', config)
            config = Config()


def _remove_from_list(key, label, config):
    vals = getattr(config, key)
    if not vals:
        clear()
        print(f"\n  {C.YELLOW}Nothing to remove.{C.RESET}")
        wait()
        return

    items = []
    for v in vals:
        items.append(MenuItem(v, action=v))
    items.append(MenuItem("Cancel", action=None))

    action = run_menu(f"Remove {label}", items)
    if action:
        _env_remove(key, action)


# ==================== Screen: Change Interval ====================

def screen_change_interval():
    config = Config()
    clear()
    print(f"{C.BOLD}{'Change Scrape Interval':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print(f"  Current interval : {C.BRIGHT_CYAN}{config.SCRAPE_INTERVAL_HOURS}h{C.RESET}")
    print(f"  Current jitter   : {C.CYAN}±{config.SCHEDULE_JITTER_MINUTES}m{C.RESET}")
    print()

    val = input_text("  New interval (hours): ")
    if val:
        try:
            _env_set('SCRAPE_INTERVAL_HOURS', val)
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Interval set to {C.CYAN}{val}h{C.RESET}")
        except ValueError:
            print(f"  {C.BRIGHT_RED}Invalid number{C.RESET}")

    val = input_text("  New jitter (minutes): ")
    if val:
        try:
            _env_set('SCHEDULE_JITTER_MINUTES', val)
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Jitter set to {C.CYAN}±{val}m{C.RESET}")
        except ValueError:
            print(f"  {C.BRIGHT_RED}Invalid number{C.RESET}")

    wait()


# ==================== Screen: Kill Switch ====================

def _count_running_processes():
    try:
        if os.name == 'nt':
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/NH'],
                capture_output=True, text=True, timeout=10
            )
            lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
            return len(lines)
        else:
            result = subprocess.run(
                ['pgrep', '-c', '-f', 'scrapy'],
                capture_output=True, text=True, timeout=10
            )
            return int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
    except Exception:
        return 0


def _list_scrape_processes():
    processes = []
    try:
        if os.name == 'nt':
            result = subprocess.run(
                ['wmic', 'process', 'where', "name='python.exe'", 'get', 'ProcessId,CommandLine', '/format:list'],
                capture_output=True, text=True, timeout=10
            )
            for block in result.stdout.split('\n\n'):
                pid = ''
                cmdline = ''
                for line in block.strip().split('\n'):
                    if line.startswith('ProcessId='):
                        pid = line.split('=', 1)[1].strip()
                    elif line.startswith('CommandLine='):
                        cmdline = line.split('=', 1)[1].strip()
                if pid and any(kw in cmdline.lower() for kw in ['scrapy', 'amazon', 'orchestrator', 'cli.py', 'monitor']):
                    processes.append((pid, cmdline))
    except Exception:
        pass
    return processes


def screen_killswitch():
    processes = _list_scrape_processes()
    count = _count_running_processes()

    if not processes and count == 0:
        clear()
        print(f"\n  {C.BRIGHT_GREEN}✓{C.RESET} No scrape processes running.")
        wait()
        return

    items = []
    items.append(MenuItem(f"Kill ALL processes ({len(processes) or count})", action="kill_all", color=C.BRIGHT_RED))

    if processes:
        items.append(MenuItem("", separator=True))
        for pid, cmdline in processes:
            short = cmdline[:50] + '...' if len(cmdline) > 50 else cmdline
            items.append(MenuItem(f"PID {pid}  {short}", action=f"kill_{pid}"))

    items.append(MenuItem("", separator=True))
    items.append(MenuItem("Back", action="back"))

    while True:
        action = run_menu("Kill Switch", items)

        if action in ("back", None):
            break
        elif action == "kill_all":
            if processes:
                for pid, _ in processes:
                    _kill_process(pid)
            else:
                _kill_all_python_scrapers()
            clear()
            print(f"\n  {C.BRIGHT_GREEN}✓{C.RESET} All scrape processes killed.")
            wait()
            break
        elif action and action.startswith("kill_"):
            pid = action[5:]
            clear()
            print(f"  Killing PID {C.BRIGHT_RED}{pid}{C.RESET}...")
            _kill_process(pid)
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Process killed.")
            wait()
            break


def _kill_process(pid):
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True, timeout=5)
        else:
            subprocess.run(['kill', '-9', str(pid)], capture_output=True, timeout=5)
    except Exception:
        pass


def _kill_all_python_scrapers():
    try:
        if os.name == 'nt':
            subprocess.run(
                ['wmic', 'process', 'where',
                 "name='python.exe' and (CommandLine like '%scrapy%' or CommandLine like '%orchestrator%')",
                 'delete'],
                capture_output=True, timeout=10
            )
        else:
            subprocess.run(['pkill', '-9', '-f', 'scrapy'], capture_output=True, timeout=5)
    except Exception:
        pass


# ==================== Input Helpers ====================

def input_text(prompt=""):
    """Read text input with visible cursor and proper terminal mode"""
    if os.name == 'nt':
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            return ""
    else:
        # Unix: temporarily restore cooked mode
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            sys.stdout.write(prompt)
            sys.stdout.flush()
            buf = []
            while True:
                ch = sys.stdin.read(1)
                if ch in ('\r', '\n'):
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    break
                elif ch == '\x7f' or ch == '\x08':
                    if buf:
                        buf.pop()
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ch == '\x1b':
                    # Esc — cancel
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    return ""
                else:
                    buf.append(ch)
                    sys.stdout.write(ch)
                    sys.stdout.flush()
            return ''.join(buf)
        except Exception:
            return ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def wait(prompt="Press Enter to continue..."):
    try:
        input(f"\n  {C.DIM}{prompt}{C.RESET}")
    except (EOFError, KeyboardInterrupt):
        pass


def _show_text_lines(lines):
    """Display a list of text lines and wait for keypress"""
    for line in lines:
        print(line)


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"


# ==================== Helpers: .env editing ====================

def _env_edit(key, value):
    env_file = Path('.env')
    if not env_file.exists():
        print(f"  {C.BRIGHT_RED}.env file not found{C.RESET}")
        return

    lines = env_file.read_text().splitlines()
    new_lines = []
    found = False

    for line in lines:
        if line.startswith(f'{key}='):
            existing = line.split('=', 1)[1].strip()
            if existing and value not in existing:
                new_val = f"{existing},{value}"
            elif not existing:
                new_val = value
            else:
                print(f"  {C.YELLOW}'{value}' already exists{C.RESET}")
                wait()
                return
            new_lines.append(f'{key}={new_val}')
            found = True
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Added '{value}'")
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}={value}')
        print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Created {key} = '{value}'")

    env_file.write_text('\n'.join(new_lines) + '\n')


def _env_remove(key, value):
    env_file = Path('.env')
    if not env_file.exists():
        return

    lines = env_file.read_text().splitlines()
    new_lines = []

    for line in lines:
        if line.startswith(f'{key}='):
            existing = line.split('=', 1)[1].strip()
            items = [x.strip() for x in existing.split(',')]
            if value in items:
                items.remove(value)
            new_val = ','.join(items)
            new_lines.append(f'{key}={new_val}')
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Removed '{value}'")
        else:
            new_lines.append(line)

    env_file.write_text('\n'.join(new_lines) + '\n')


def _env_set(key, value):
    env_file = Path('.env')
    if not env_file.exists():
        print(f"  {C.BRIGHT_RED}.env file not found{C.RESET}")
        return

    lines = env_file.read_text().splitlines()
    new_lines = []
    found = False

    for line in lines:
        if line.startswith(f'{key}='):
            new_lines.append(f'{key}={value}')
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}={value}')

    env_file.write_text('\n'.join(new_lines) + '\n')


# ==================== Entry Point ====================

def main():
    try:
        show_main_menu()
    except KeyboardInterrupt:
        clear()
        print(f"\n  {C.DIM}Goodbye! 👋{C.RESET}\n")
    except Exception as e:
        clear()
        print(f"\n  {C.BRIGHT_RED}Error: {e}{C.RESET}")
        import traceback
        traceback.print_exc()
        print()


if __name__ == '__main__':
    main()
