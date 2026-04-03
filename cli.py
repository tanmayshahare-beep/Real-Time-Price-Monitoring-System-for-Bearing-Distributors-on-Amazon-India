#!/usr/bin/env python
"""
CLI for Amazon Price Monitor - Interactive menu-driven interface.
When opened, shows a dashboard with numbered options to choose from.

Usage:
    python cli.py              Open interactive menu (default)
    python cli.py --quick      Show quick-help for direct commands
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
from warmup_manager import ScrapePatternRandomizer, BehavioralScheduler, DirectASINChecker
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
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def wait(prompt="Press Enter to continue..."):
    try:
        input(f"\n  {C.DIM}{prompt}{C.RESET}")
    except (EOFError, KeyboardInterrupt):
        pass


# ==================== Screen: Main Menu ====================

def draw_header():
    print(f"{C.BRIGHT_CYAN}{'═'*60}{C.RESET}")
    print(f"{C.BOLD}     Amazon Price Monitor - Control Panel{C.RESET}")
    print(f"{C.DIM}     Real-Time Price Monitoring for Amazon India{C.RESET}")
    now = datetime.now().strftime('%A, %d %B %Y  •  %H:%M:%S')
    print(f"{C.DIM}     {now}{C.RESET}")
    print(f"{C.BRIGHT_CYAN}{'═'*60}{C.RESET}")


def draw_status_strip():
    """One-line status summary at the top"""
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


def show_main_menu():
    while True:
        clear()
        draw_header()
        print()
        draw_status_strip()

        print(f"  {C.BOLD}{C.BRIGHT_CYAN}SCRAPING{C.RESET}")
        print(f"    {C.BOLD}1{C.RESET}. Run Scrape (default query)")
        print(f"    {C.BOLD}2{C.RESET}. Run Scrape (custom query)")
        print(f"    {C.BOLD}3{C.RESET}. Run Scrape with decoy queries")
        print(f"    {C.BOLD}4{C.RESET}. Start Continuous Monitoring")
        print()

        print(f"  {C.BOLD}{C.BRIGHT_MAGENTA}ANALYSIS{C.RESET}")
        print(f"    {C.BOLD}5{C.RESET}. Run AI Price Analysis")
        print()

        print(f"  {C.BOLD}{C.BRIGHT_GREEN}STATUS & REPORTS{C.RESET}")
        print(f"    {C.BOLD}6{C.RESET}. View Session Status")
        print(f"    {C.BOLD}7{C.RESET}. View Price Alerts")
        print(f"    {C.BOLD}8{C.RESET}. Export Session Report")
        print()

        print(f"  {C.BOLD}{C.BRIGHT_YELLOW}LOGS{C.RESET}")
        print(f"    {C.BOLD}9{C.RESET}. View Activity Log")
        print(f"    {C.BOLD}10{C.RESET}. View Errors Only")
        print(f"    {C.BOLD}11{C.RESET}. Search Logs")
        print(f"    {C.BOLD}12{C.RESET}. View Scraper Log")
        print()

        print(f"  {C.BOLD}{C.BRIGHT_BLUE}CONFIGURATION{C.RESET}")
        print(f"    {C.BOLD}13{C.RESET}. Show Configuration")
        print(f"    {C.BOLD}14{C.RESET}. Manage Queries & ASINs")
        print(f"    {C.BOLD}15{C.RESET}. Change Scrape Interval")
        print()

        print(f"  {C.BOLD}{C.BRIGHT_RED}CONTROL{C.RESET}")
        running = _count_running_processes()
        if running > 0:
            print(f"    {C.BOLD}16{C.RESET}. {C.BRIGHT_RED}Kill Switch{C.RESET} ({C.BRIGHT_RED}{running} process(es) running{C.RESET})")
        else:
            print(f"    {C.BOLD}16{C.RESET}. Kill Switch ({C.GREEN}all clear{C.RESET})")
        print()

        print(f"    {C.BOLD}0{C.RESET}. Exit")
        print()

        choice = input(f"  {C.BRIGHT_CYAN}Select option{C.RESET}: ").strip()

        if choice == '0':
            clear()
            print(f"\n  {C.DIM}Goodbye! 👋{C.RESET}\n")
            break
        elif choice == '1':
            screen_scrape()
        elif choice == '2':
            screen_scrape_custom()
        elif choice == '3':
            screen_scrape_with_decoy()
        elif choice == '4':
            screen_monitor()
        elif choice == '5':
            screen_analyze()
        elif choice == '6':
            screen_status()
        elif choice == '7':
            screen_price_alerts()
        elif choice == '8':
            screen_report()
        elif choice == '9':
            screen_activity_log()
        elif choice == '10':
            screen_errors()
        elif choice == '11':
            screen_search_logs()
        elif choice == '12':
            screen_scraper_log()
        elif choice == '13':
            screen_config()
        elif choice == '14':
            screen_manage_queries()
        elif choice == '15':
            screen_change_interval()
        elif choice == '16':
            screen_killswitch()


# ==================== Screen: Scrape ====================

def screen_scrape():
    config = Config()
    if not config.TARGET_QUERIES:
        clear()
        print(f"\n  {C.BRIGHT_RED}No target queries configured. Go to option 14 first.{C.RESET}")
        wait()
        return

    query = config.TARGET_QUERIES[0]
    run_scrape(query, decoy=False)


def screen_scrape_custom():
    clear()
    print(f"{C.BOLD}{'Custom Scrape':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")
    query = input(f"  Enter search query: ").strip()
    if not query:
        wait()
        return
    run_scrape(query, decoy=False)


def screen_scrape_with_decoy():
    config = Config()
    if not config.TARGET_QUERIES:
        clear()
        print(f"\n  {C.BRIGHT_RED}No target queries configured.{C.RESET}")
        wait()
        return

    query = config.TARGET_QUERIES[0]
    run_scrape(query, decoy=True)


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

    # Decoy scrape first
    if decoy and config.DECOY_QUERIES:
        decoy_query = config.get_random_decoy_query()
        print(f"  {C.DIM}[decoy]{C.RESET} Scraping: {C.CYAN}{decoy_query}{C.RESET}")
        count = _run_scrapy(decoy_query)
        print(f"  {C.DIM}Delaying (human-like pause)...{C.RESET}\n")
        timing.between_searches()

    # Main scrape
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

    choice = input(f"  Start now? ({C.BOLD}Y{C.RESET}/n): ").strip().lower()
    if choice == 'n':
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

    # Show available ASINs from stats
    clear()
    print(f"{C.BOLD}{'AI Price Analysis':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")

    if stats_tracker.products:
        print(f"  {C.BOLD}Tracked ASINs:{C.RESET}")
        for i, (asin, prod) in enumerate(stats_tracker.products.items(), 1):
            print(f"    {i}. {C.CYAN}{asin}{C.RESET}  (last: ₹{prod.current_price})")
        print()

    if config.MONITORED_ASINS:
        print(f"  {C.BOLD}Monitored ASINs (from config):{C.RESET}")
        for i, asin in enumerate(config.MONITORED_ASINS, len(stats_tracker.products) + 1):
            print(f"    {i}. {C.CYAN}{asin}{C.RESET}")
        print()

    print(f"    {C.BOLD}C{C.RESET}. Custom ASIN")
    print()

    choice = input(f"  Select ASIN: ").strip()

    if not choice:
        wait()
        return

    if choice.upper() == 'C':
        asin = input(f"  Enter ASIN: ").strip()
    else:
        try:
            idx = int(choice) - 1
            all_asins = list(stats_tracker.products.keys()) + config.MONITORED_ASINS
            if 0 <= idx < len(all_asins):
                asin = all_asins[idx]
            else:
                print(f"  {C.BRIGHT_RED}Invalid selection{C.RESET}")
                wait()
                return
        except ValueError:
            print(f"  {C.BRIGHT_RED}Invalid input{C.RESET}")
            wait()
            return

    if not asin:
        wait()
        return

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
    print(f"{C.BOLD}{'Session Status':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")

    tracker = stats_tracker
    summary = tracker.get_session_summary()

    if not summary.get('session_start'):
        print(f"  {C.YELLOW}No active session. Run a scrape first.{C.RESET}")
        wait()
        return

    print(f"  Session started : {C.BRIGHT_CYAN}{summary['session_start']}{C.RESET}")
    print(f"  Elapsed time    : {C.CYAN}{summary['elapsed_time']}{C.RESET}")
    print(f"  Queries run     : {C.BOLD}{summary['queries']['run']}{C.RESET}")
    print()
    print(f"  Products scraped : {C.BRIGHT_GREEN}{summary['products']['scraped']}{C.RESET}")
    print(f"  Products failed  : {C.BRIGHT_RED}{summary['products']['failed']}{C.RESET}")
    print(f"  Price changes    : {C.BRIGHT_YELLOW}{summary['activities']['price_changes']}{C.RESET}")
    print(f"  Analyses run     : {C.BRIGHT_MAGENTA}{summary['activities']['analyses']}{C.RESET}")
    print(f"  Errors           : {C.BRIGHT_RED}{summary['activities']['errors']}{C.RESET}")
    print()

    if tracker.products:
        print(f"  {C.BOLD}Products{C.RESET}")
        print(f"  {'─'*58}")
        print(f"  {'ASIN':<15} {'Price':<10} {'Low':<10} {'High':<10} {'Changes':<8} {'Status'}")
        print(f"  {'─'*58}")
        for asin, prod in tracker.products.items():
            sc = C.GREEN if prod.status == 'scraped' else C.RED if prod.status == 'error' else C.YELLOW
            print(f"  {C.CYAN}{asin:<15}{C.RESET} {C.GREEN}₹{prod.current_price:<9}{C.RESET} {C.GREEN}₹{prod.lowest_price:<9}{C.RESET} {C.YELLOW}₹{prod.highest_price:<9}{C.RESET} {prod.price_changes:<8} {sc}{prod.status}{C.RESET}")
        print()

    progress = tracker.get_progress_percentage()
    bar_len = 40
    filled = int(bar_len * progress / 100) if tracker.session.products_total else 0
    bar = f"{C.GREEN}{'█'*filled}{C.RESET}{'░'*(bar_len-filled)}"
    print(f"  Progress: [{bar}] {progress:.1f}%")
    wait()


# ==================== Screen: Price Alerts ====================

def screen_price_alerts():
    clear()
    print(f"{C.BOLD}{'Price Change Alerts':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")

    alerts = stats_tracker.get_price_alerts()
    if not alerts:
        print(f"  {C.YELLOW}No price changes detected yet.{C.RESET}")
    else:
        for i, a in enumerate(alerts, 1):
            print(f"  {C.BOLD}{i}.{C.RESET} {C.CYAN}{a['asin']}{C.RESET}")
            print(f"     Title   : {a['title'][:50]}")
            print(f"     Current : {C.GREEN}₹{a['current_price']}{C.RESET}")
            print(f"     Range   : {C.GREEN}₹{a['lowest_price']}{C.RESET} - {C.YELLOW}₹{a['highest_price']}{C.RESET}")
            print(f"     Changes : {C.BOLD}{a['changes']}{C.RESET}")
            print(f"     Updated : {a['last_updated']}")
            print()
    wait()


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
    print(f"{C.BOLD}{'Session Report':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")
    print(f"  Session  : {C.BRIGHT_CYAN}{summary['session_start']}{C.RESET}")
    print(f"  Elapsed  : {C.CYAN}{summary['elapsed_time']}{C.RESET}")
    print(f"  Scraped  : {C.BRIGHT_GREEN}{summary['products']['scraped']}{C.RESET}")
    print(f"  Failed   : {C.BRIGHT_RED}{summary['products']['failed']}{C.RESET}")
    print(f"  Changes  : {C.BRIGHT_YELLOW}{summary['activities']['price_changes']}{C.RESET}")
    print(f"  Errors   : {C.BRIGHT_RED}{summary['activities']['errors']}{C.RESET}")
    print()
    print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Saved to {C.BOLD}{filename}{C.RESET}")
    wait()


# ==================== Screen: Logs ====================

def screen_activity_log():
    viewer = LogViewer()
    clear()
    print(f"{C.BOLD}{'Activity Log':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")

    types = ['ALL', 'SCRAPE', 'ANALYSIS', 'SCHEDULE', 'ERROR', 'BLOCKED', 'PROXY']
    for i, t in enumerate(types, 1):
        print(f"    {C.BOLD}{i}{C.RESET}. {t}")
    print()

    choice = input(f"  Filter type ({C.BOLD}1{C.RESET}-{len(types)}): ").strip()
    try:
        idx = int(choice) - 1
        filter_type = types[idx] if 0 <= idx < len(types) else None
        if filter_type == 'ALL':
            filter_type = None
    except (ValueError, IndexError):
        filter_type = None

    viewer.view_activity_log(50, filter_type)
    wait()


def screen_errors():
    viewer = LogViewer()
    viewer.view_errors()
    wait()


def screen_search_logs():
    clear()
    query = input(f"  Search logs for: ").strip()
    if not query:
        wait()
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
    clear()
    print(f"{C.BOLD}{'Configuration':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")

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
            ('Offers read', f"{config.READING_TIME_OFFERS_MIN}-{config.READING_TIME_OFFERS_MAX}s"),
            ('Between searches', f"{config.BETWEEN_SEARCHES_MIN}-{config.BETWEEN_SEARCHES_MAX}s"),
            ('Hesitation', config.HESITATION_PROBABILITY),
        ]),
        ('Infrastructure', [
            ('MongoDB', config.MONGO_URI),
            ('Proxies', len(config.PROXY_LIST)),
            ('Ollama', config.OLLAMA_MODEL),
        ]),
    ]

    for section, items in sections:
        print(f"  {C.BOLD}{C.BRIGHT_CYAN}{section}{C.RESET}")
        print(f"  {'─'*50}")
        for key, val in items:
            print(f"  {C.DIM}{key:<22}{C.RESET} {val}")
        print()

    wait()


def screen_manage_queries():
    config = Config()
    while True:
        clear()
        print(f"{C.BOLD}{'Manage Queries & ASINs':^60}")
        print(f"{C.DIM}{'─'*60}{C.RESET}\n")

        print(f"  {C.BOLD}Target Queries:{C.RESET}")
        for i, q in enumerate(config.TARGET_QUERIES, 1):
            print(f"    {i}. {C.GREEN}{q}{C.RESET}")
        print()

        print(f"  {C.BOLD}Decoy Queries:{C.RESET}")
        for i, q in enumerate(config.DECOY_QUERIES, 1):
            print(f"    {i}. {C.YELLOW}{q}{C.RESET}")
        print()

        if config.MONITORED_ASINS:
            print(f"  {C.BOLD}Monitored ASINs:{C.RESET}")
            for i, a in enumerate(config.MONITORED_ASINS, 1):
                print(f"    {i}. {C.CYAN}{a}{C.RESET}")
            print()

        print(f"    {C.BOLD}1{C.RESET}. Add target query")
        print(f"    {C.BOLD}2{C.RESET}. Add decoy query")
        print(f"    {C.BOLD}3{C.RESET}. Add monitored ASIN")
        print(f"    {C.BOLD}4{C.RESET}. Remove target query")
        print(f"    {C.BOLD}5{C.RESET}. Remove decoy query")
        print(f"    {C.BOLD}6{C.RESET}. Remove monitored ASIN")
        print(f"    {C.BOLD}0{C.RESET}. Back")
        print()

        choice = input(f"  Select: ").strip()

        if choice == '0':
            break
        elif choice == '1':
            val = input(f"  Query to add: ").strip()
            if val:
                _env_edit('TARGET_QUERIES', val)
                config = Config()  # reload
        elif choice == '2':
            val = input(f"  Decoy query to add: ").strip()
            if val:
                _env_edit('DECOY_QUERIES', val)
                config = Config()
        elif choice == '3':
            val = input(f"  ASIN to add: ").strip()
            if val:
                _env_edit('MONITORED_ASINS', val)
                config = Config()
        elif choice in ('4', '5', '6'):
            key_map = {'4': 'TARGET_QUERIES', '5': 'DECOY_QUERIES', '6': 'MONITORED_ASINS'}
            key = key_map[choice]
            vals = config.TARGET_QUERIES if choice == '4' else (config.DECOY_QUERIES if choice == '5' else config.MONITORED_ASINS)
            if not vals:
                print(f"  {C.YELLOW}Nothing to remove{C.RESET}")
                wait()
                continue

            clear()
            print(f"  {C.BOLD}Select item to remove:{C.RESET}\n")
            for i, v in enumerate(vals, 1):
                print(f"    {i}. {v}")
            print()

            sel = input(f"  Select: ").strip()
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(vals):
                    _env_remove(key, vals[idx])
                    config = Config()
            except ValueError:
                pass
        else:
            wait("Invalid choice")


def screen_change_interval():
    config = Config()
    clear()
    print(f"{C.BOLD}{'Change Scrape Interval':^60}")
    print(f"{C.DIM}{'─'*60}{C.RESET}\n")
    print(f"  Current interval : {C.BRIGHT_CYAN}{config.SCRAPE_INTERVAL_HOURS}h{C.RESET}")
    print(f"  Current jitter   : {C.CYAN}±{config.SCHEDULE_JITTER_MINUTES}m{C.RESET}")
    print()

    val = input(f"  New interval (hours): ").strip()
    if val:
        try:
            _env_set('SCRAPE_INTERVAL_HOURS', val)
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Interval set to {C.CYAN}{val}h{C.RESET}")
        except ValueError:
            print(f"  {C.BRIGHT_RED}Invalid number{C.RESET}")

    val = input(f"  New jitter (minutes, or Enter to keep): ").strip()
    if val:
        try:
            _env_set('SCHEDULE_JITTER_MINUTES', val)
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Jitter set to {C.CYAN}±{val}m{C.RESET}")
        except ValueError:
            print(f"  {C.BRIGHT_RED}Invalid number{C.RESET}")

    wait()


# ==================== Screen: Kill Switch ====================

def _count_running_processes():
    """Count running scrape-related processes"""
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
    """List running scrape processes with PIDs"""
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

                if pid and ('scrapy' in cmdline.lower() or 'amazon' in cmdline.lower() or 'orchestrator' in cmdline.lower() or 'cli.py' in cmdline.lower()):
                    processes.append((pid, cmdline))
        else:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split('\n'):
                if any(kw in line.lower() for kw in ['scrapy', 'orchestrator', 'amazon']):
                    parts = line.split()
                    if len(parts) > 1:
                        processes.append((parts[1], ' '.join(parts[10:])))
    except Exception:
        pass
    return processes


def screen_killswitch():
    """Kill switch screen - shows running processes and lets you kill them"""
    while True:
        clear()
        print(f"{C.BOLD}{'Kill Switch':^60}")
        print(f"{C.DIM}{'─'*60}{C.RESET}\n")

        processes = _list_scrape_processes()
        count = _count_running_processes()

        if not processes and count == 0:
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} No scrape processes running.")
            print()
            wait()
            return

        print(f"  {C.BRIGHT_RED}{len(processes) or count} process(es) found:{C.RESET}\n")

        for i, (pid, cmdline) in enumerate(processes, 1):
            # Truncate long command lines
            if len(cmdline) > 55:
                cmdline = cmdline[:52] + '...'
            print(f"  {C.BOLD}{i}.{C.RESET} PID: {C.BRIGHT_RED}{pid:<8}{C.RESET} {C.DIM}{cmdline}{C.RESET}")

        if not processes:
            print(f"  {C.DIM}(Processes detected but details unavailable){C.RESET}")
            print()

        print()
        print(f"  {C.BOLD}1{C.RESET}. Kill {C.BRIGHT_RED}all{C.RESET} scrape processes")
        if processes:
            print(f"  {C.BOLD}2{C.RESET}. Kill specific process (by number)")
        print(f"  {C.BOLD}0{C.RESET}. Back")
        print()

        choice = input(f"  {C.BRIGHT_CYAN}Select{C.RESET}: ").strip()

        if choice == '0':
            break
        elif choice == '1':
            if processes:
                for pid, _ in processes:
                    _kill_process(pid)
            else:
                # Kill all python processes related to scraper
                _kill_all_python_scrapers()
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} All scrape processes killed.")
            wait()
            break
        elif choice == '2' and processes:
            sel = input(f"  Process number: ").strip()
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(processes):
                    pid, cmdline = processes[idx]
                    print(f"  Killing PID {C.BRIGHT_RED}{pid}{C.RESET}...")
                    _kill_process(pid)
                    print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Process killed.")
                    wait()
            except ValueError:
                pass


def _kill_process(pid):
    """Kill a process by PID"""
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                         capture_output=True, timeout=5)
        else:
            subprocess.run(['kill', '-9', str(pid)],
                         capture_output=True, timeout=5)
    except Exception:
        pass


def _kill_all_python_scrapers():
    """Kill all python processes with scrapy/monitor keywords"""
    try:
        if os.name == 'nt':
            # Kill scrapy processes
            subprocess.run(
                ['wmic', 'process', 'where',
                 "name='python.exe' and (CommandLine like '%scrapy%' or CommandLine like '%orchestrator%')",
                 'delete'],
                capture_output=True, timeout=10
            )
        else:
            subprocess.run(
                ['pkill', '-9', '-f', 'scrapy'],
                capture_output=True, timeout=5
            )
    except Exception:
        pass


# ==================== Helpers ====================

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


def format_duration(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"


# ==================== Entry Point ====================

def main():
    if '--quick' in sys.argv or '-q' in sys.argv:
        print("Usage:")
        print("  python cli.py              Open interactive menu")
        print("  python cli.py --quick      Show this help")
        print()
        return

    try:
        show_main_menu()
    except KeyboardInterrupt:
        clear()
        print(f"\n  {C.DIM}Goodbye! 👋{C.RESET}\n")


if __name__ == '__main__':
    main()
