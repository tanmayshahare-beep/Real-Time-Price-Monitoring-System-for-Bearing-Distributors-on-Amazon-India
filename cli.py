#!/usr/bin/env python
"""
CLI for Amazon Price Monitor - Full control interface.
Manages scrapes, monitoring, logs, stats, config, and analysis.

Usage:
    python cli.py scrape [QUERY]          Run a single scrape
    python cli.py monitor                 Start continuous monitoring
    python cli.py analyze [ASIN]          Run AI analysis for an ASIN
    python cli.py status                  Show current session status
    python cli.py logs [OPTIONS]          View and filter logs
    python cli.py config [OPTIONS]        View/edit configuration
    python cli.py report                  Export session report
    python cli.py interactive             Launch interactive menu
"""
import argparse
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


# ==================== Color Utilities ====================

class C:
    """ANSI color codes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    BLACK = '\033[30m'
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


def banner():
    """Print CLI banner"""
    print()
    print(f"{C.BRIGHT_CYAN}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  Amazon Price Monitor - CLI{C.RESET}")
    print(f"{C.DIM}  Real-Time Price Monitoring for Amazon India{C.RESET}")
    print(f"{C.BRIGHT_CYAN}{'='*60}{C.RESET}")
    print()


def format_duration(seconds):
    """Format seconds to human-readable"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"


# ==================== Command Handlers ====================

def cmd_scrape(args):
    """Run a single scrape session"""
    config = Config()
    query = args.query if args.query else (config.TARGET_QUERIES[0] if config.TARGET_QUERIES else 'SKF bearing 6205')
    decoy = args.decoy

    banner()
    print(f"{C.BOLD}{'Scrape Session':^60}{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print(f"  Target query : {C.BRIGHT_GREEN}{query}{C.RESET}")

    if decoy:
        print(f"  Decoy queries: {C.YELLOW}enabled{C.RESET}")

    print(f"  Human timing: {C.BRIGHT_GREEN}enabled{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print()

    activity_logger.log_session_start(query)
    stats_tracker.initialize_session([query])

    timing = HumanTiming()
    scheduler = BehavioralScheduler(config)
    randomizer = ScrapePatternRandomizer(config)

    # Optional decoy scrape
    if decoy and config.DECOY_QUERIES:
        decoy_query = config.get_random_decoy_query()
        print(f"  {C.DIM}[decoy]{C.RESET} Scraping: {C.CYAN}{decoy_query}{C.RESET}")
        _run_scrapy_scrape(decoy_query)
        print(f"  {C.DIM}Delaying...{C.RESET}")
        timing.between_searches()
        print()

    # Main scrape
    print(f"  {C.BOLD}[target]{C.RESET} Scraping: {C.BRIGHT_GREEN}{query}{C.RESET}")
    start = time.time()
    products = _run_scrapy_scrape(query)
    elapsed = time.time() - start

    if products > 0:
        print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Scraped {C.BOLD}{products}{C.RESET} product(s) in {C.CYAN}{format_duration(elapsed)}{C.RESET}")
        activity_logger.log_session_end(query, products)
    else:
        print(f"  {C.BRIGHT_RED}✗{C.RESET} No products scraped (possible blocking or no results)")
        activity_logger.log_error(query, 'No products scraped', 'Scrape')

    print()
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print(f"  Session complete at {datetime.now().strftime('%H:%M:%S')}")
    print()


def _run_scrapy_scrape(query):
    """Run scrapy crawl and return product count"""
    try:
        result = subprocess.run(
            ['scrapy', 'crawl', 'amazon', '-a', f'query={query}'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            count = sum(1 for line in result.stdout.split('\n') if 'Scraped ASIN' in line)
            return count if count > 0 else 1
        return 0
    except subprocess.TimeoutExpired:
        return 0
    except Exception:
        return 0


def cmd_monitor(args):
    """Start continuous monitoring"""
    config = Config()
    interval = args.interval if args.interval else config.SCRAPE_INTERVAL_HOURS

    banner()
    print(f"{C.BOLD}{'Continuous Monitoring':^60}{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print(f"  Interval     : {C.BRIGHT_CYAN}{interval}h{C.RESET} (±{config.SCHEDULE_JITTER_MINUTES}m jitter)")
    print(f"  Target queries: {C.BRIGHT_GREEN}{', '.join(config.TARGET_QUERIES)}{C.RESET}")
    print(f"  Decoy queries : {C.YELLOW}{', '.join(config.DECOY_QUERIES)}{C.RESET}")
    print(f"  Human timing  : {C.BRIGHT_GREEN}enabled{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print()
    print(f"  {C.DIM}Press Ctrl+C to stop{C.RESET}")
    print()

    from orchestrator import AmazonMonitorOrchestrator
    monitor = AmazonMonitorOrchestrator(config)

    try:
        monitor.run_scheduled_monitoring()
    except KeyboardInterrupt:
        print(f"\n  {C.YELLOW}Monitoring stopped by user{C.RESET}")
        print()


def cmd_analyze(args):
    """Run AI analysis for an ASIN"""
    config = Config()
    asin = args.asin

    if not asin:
        # Try to get from monitored ASINs
        if config.MONITORED_ASINS:
            asin = config.MONITORED_ASINS[0]
        else:
            print(f"{C.BRIGHT_RED}No ASIN provided and no MONITORED_ASINS configured.{C.RESET}")
            print(f"Usage: python cli.py analyze B0XXXXXXXX")
            return

    banner()
    print(f"{C.BOLD}{'AI Analysis':^60}{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print(f"  ASIN  : {C.BRIGHT_CYAN}{asin}{C.RESET}")
    print(f"  Model : {C.DIM}{config.OLLAMA_MODEL}{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")
    print()

    activity_logger.log_session_start(f"analysis-{asin}")
    print(f"  {C.DIM}Running analysis...{C.RESET}\n")

    try:
        result = subprocess.run(
            ['python', '-m', 'analysis.analyze', asin],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            # Colorize key sections
            for line in output.split('\n'):
                if 'trend' in line.lower() or 'stable' in line.lower():
                    print(f"  {C.BRIGHT_CYAN}{line}{C.RESET}")
                elif 'price' in line.lower() or '₹' in line:
                    print(f"  {C.BRIGHT_GREEN}{line}{C.RESET}")
                elif 'recommend' in line.lower() or 'adjust' in line.lower():
                    print(f"  {C.BRIGHT_YELLOW}{line}{C.RESET}")
                else:
                    print(f"  {C.WHITE}{line}{C.RESET}")
            activity_logger.log_analysis(asin, output[:200])
            stats_tracker.log_analysis(asin, output)
        else:
            print(f"  {C.BRIGHT_RED}✗ Analysis failed: {result.stderr[:300]}{C.RESET}")

    except subprocess.TimeoutExpired:
        print(f"  {C.BRIGHT_RED}✗ Analysis timed out (120s){C.RESET}")
    except FileNotFoundError:
        print(f"  {C.BRIGHT_RED}✗ Ollama not running. Start it with: ollama serve{C.RESET}")
    except Exception as e:
        print(f"  {C.BRIGHT_RED}✗ Error: {e}{C.RESET}")

    print()


def cmd_status(args):
    """Show current session/product status"""
    banner()
    print(f"{C.BOLD}{'Monitor Status':^60}{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")

    tracker = stats_tracker
    summary = tracker.get_session_summary()

    if not summary['session_start']:
        print(f"  {C.YELLOW}No active session. Run a scrape first.{C.RESET}")
        print()
        return

    # Session info
    print(f"  Session started : {C.BRIGHT_CYAN}{summary['session_start']}{C.RESET}")
    print(f"  Elapsed time    : {C.CYAN}{summary['elapsed_time']}{C.RESET}")
    print(f"  Queries run     : {C.BOLD}{summary['queries']['run']}{C.RESET}")
    print()

    # Products
    print(f"  {C.BOLD}Products{C.RESET}")
    print(f"    Total    : {summary['products']['total']}")
    print(f"    Scraped  : {C.BRIGHT_GREEN}{summary['products']['scraped']}{C.RESET}")
    print(f"    Failed   : {C.BRIGHT_RED}{summary['products']['failed']}{C.RESET}")
    print()

    # Activities
    print(f"  {C.BOLD}Activity{C.RESET}")
    print(f"    Price changes : {C.BRIGHT_YELLOW}{summary['activities']['price_changes']}{C.RESET}")
    print(f"    Analyses run  : {C.BRIGHT_MAGENTA}{summary['activities']['analyses']}{C.RESET}")
    print(f"    Errors        : {C.BRIGHT_RED}{summary['activities']['errors']}{C.RESET}")
    print()

    # Product details
    if tracker.products:
        print(f"  {C.BOLD}Tracked Products{C.RESET}")
        print(f"  {'─'*58}")
        print(f"  {'ASIN':<15} {'Price':<10} {'Low':<10} {'High':<10} {'Changes':<8} {'Status'}")
        print(f"  {'─'*58}")
        for asin, prod in tracker.products.items():
            status_color = C.GREEN if prod.status == 'scraped' else C.RED if prod.status == 'error' else C.YELLOW
            print(f"  {C.CYAN}{asin:<15}{C.RESET} {C.GREEN}₹{prod.current_price:<9}{C.RESET} {C.GREEN}₹{prod.lowest_price:<9}{C.RESET} {C.YELLOW}₹{prod.highest_price:<9}{C.RESET} {prod.price_changes:<8} {status_color}{prod.status}{C.RESET}")
        print()

    # Recent activities
    activities = tracker.get_recent_activities(5)
    if activities:
        print(f"  {C.BOLD}Recent Activity{C.RESET}")
        print(f"  {'─'*58}")
        for act in activities:
            type_colors = {
                'SCRAPE': C.BRIGHT_CYAN,
                'ANALYSIS': C.BRIGHT_MAGENTA,
                'QUERY': C.BRIGHT_BLUE,
                'ERROR': C.BRIGHT_RED,
            }
            color = type_colors.get(act['type'], C.WHITE)
            print(f"  [{act['timestamp']}] {color}{act['type']:<10}{C.RESET} {act['details'][:40]}")
        print()

    # Progress
    progress = tracker.get_progress_percentage()
    bar_len = 40
    filled = int(bar_len * progress / 100)
    bar = f"{C.GREEN}{'█'*filled}{C.RESET}{'░'*(bar_len-filled)}"
    print(f"  Progress: [{bar}] {progress:.1f}%")
    print()


def cmd_logs(args):
    """View and filter logs"""
    from log_viewer import LogViewer
    viewer = LogViewer()

    if args.errors:
        viewer.view_errors(args.limit)
    elif args.prices:
        viewer.view_price_alerts(args.limit)
    elif args.search:
        viewer.search(args.search)
    elif args.type:
        viewer.view_activity_log(args.limit, args.type.upper())
    elif args.tail:
        viewer.view_activity_log(args.limit)
    elif args.scraper:
        level = args.level.upper() if args.level else 'INFO'
        viewer.view_bot_log(args.limit, level)
    else:
        viewer.view_activity_log(args.limit)


def cmd_config(args):
    """View/edit configuration"""
    config = Config()

    if args.show:
        banner()
        print(f"{C.BOLD}{'Configuration':^60}{C.RESET}")
        print(f"{C.DIM}{'─'*60}{C.RESET}")

        sections = {
            'Amazon': [
                ('Domain', config.AMAZON_DOMAIN),
                ('Target queries', ', '.join(config.TARGET_QUERIES)),
                ('Decoy queries', ', '.join(config.DECOY_QUERIES)),
                ('Monitored ASINs', ', '.join(config.MONITORED_ASINS) if config.MONITORED_ASINS else '(none)'),
            ],
            'Scheduling': [
                ('Interval', f"{config.SCRAPE_INTERVAL_HOURS}h"),
                ('Jitter', f"±{config.SCHEDULE_JITTER_MINUTES}m"),
                ('ASIN check delay', f"{config.ASIN_CHECK_DELAY_MIN}-{config.ASIN_CHECK_DELAY_MAX}s"),
            ],
            'Behavioral': [
                ('Request delay', f"{config.REQUEST_DELAY_MIN}-{config.REQUEST_DELAY_MAX}s"),
                ('Search read time', f"{config.READING_TIME_SEARCH_MIN}-{config.READING_TIME_SEARCH_MAX}s"),
                ('Product read time', f"{config.READING_TIME_PRODUCT_MIN}-{config.READING_TIME_PRODUCT_MAX}s"),
                ('Offers read time', f"{config.READING_TIME_OFFERS_MIN}-{config.READING_TIME_OFFERS_MAX}s"),
                ('Between searches', f"{config.BETWEEN_SEARCHES_MIN}-{config.BETWEEN_SEARCHES_MAX}s"),
                ('Session start delay', f"{config.SESSION_START_DELAY_MIN}-{config.SESSION_START_DELAY_MAX}s"),
                ('Hesitation prob.', config.HESITATION_PROBABILITY),
            ],
            'Scrapy': [
                ('Concurrent requests', config.CONCURRENT_REQUESTS),
                ('Download delay', config.DOWNLOAD_DELAY),
                ('Retry times', config.RETRY_TIMES),
                ('User agents', len(config.USER_AGENTS)),
            ],
            'Infrastructure': [
                ('MongoDB', config.MONGO_URI),
                ('Database', config.MONGO_DB),
                ('Proxies', len(config.PROXY_LIST) if config.PROXY_LIST else 0),
                ('Ollama URL', config.OLLAMA_URL),
                ('Ollama model', config.OLLAMA_MODEL),
            ],
        }

        for section, items in sections.items():
            print(f"\n  {C.BOLD}{C.BRIGHT_CYAN}{section}{C.RESET}")
            print(f"  {'─'*50}")
            for key, val in items:
                print(f"  {C.DIM}{key:<22}{C.RESET} {val}")
        print()

    elif args.list_queries:
        print(f"\n{C.BOLD}Target queries:{C.RESET}")
        for q in config.TARGET_QUERIES:
            print(f"  {C.GREEN}• {q}{C.RESET}")
        print(f"\n{C.BOLD}Decoy queries:{C.RESET}")
        for q in config.DECOY_QUERIES:
            print(f"  {C.YELLOW}• {q}{C.RESET}")
        if config.MONITORED_ASINS:
            print(f"\n{C.BOLD}Monitored ASINs:{C.RESET}")
            for a in config.MONITORED_ASINS:
                print(f"  {C.CYAN}• {a}{C.RESET}")
        print()

    elif args.add_query:
        _env_edit('TARGET_QUERIES', args.add_query)
    elif args.add_decoy:
        _env_edit('DECOY_QUERIES', args.add_decoy)
    elif args.add_asin:
        _env_edit('MONITORED_ASINS', args.add_asin)
    elif args.set_interval:
        _env_set('SCRAPE_INTERVAL_HOURS', str(args.set_interval))
    elif args.set_jitter:
        _env_set('SCHEDULE_JITTER_MINUTES', str(args.set_jitter))

    else:
        print(f"  {C.YELLOW}No action specified. Use --show, --list-queries, --add-query, etc.{C.RESET}")
        print(f"  Run {C.CYAN}python cli.py config --help{C.RESET} for options.")
        print()


def _env_edit(key, value):
    """Append a value to a comma-separated env var in .env"""
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
                print(f"  {C.YELLOW}'{value}' already exists in {key}{C.RESET}")
                return
            new_lines.append(f'{key}={new_val}')
            found = True
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Added '{value}' to {C.BOLD}{key}{C.RESET}")
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}={value}')
        print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Created {C.BOLD}{key}{C.RESET} = '{value}'")

    env_file.write_text('\n'.join(new_lines) + '\n')


def _env_set(key, value):
    """Set a value in .env"""
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
            print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Set {C.BOLD}{key}{C.RESET} = {C.CYAN}{value}{C.RESET}")
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}={value}')
        print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Created {C.BOLD}{key}{C.RESET} = {C.CYAN}{value}{C.RESET}")

    env_file.write_text('\n'.join(new_lines) + '\n')


def cmd_report(args):
    """Export session report"""
    banner()
    print(f"{C.BOLD}{'Session Report':^60}{C.RESET}")
    print(f"{C.DIM}{'─'*60}{C.RESET}")

    tracker = stats_tracker

    if not tracker.products and not tracker.session.start_time:
        print(f"  {C.YELLOW}No data to report. Run a scrape first.{C.RESET}")
        print()
        return

    filename = args.output if args.output else f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    tracker.export_report(filename)

    summary = tracker.get_session_summary()
    print(f"  Session started : {C.BRIGHT_CYAN}{summary['session_start']}{C.RESET}")
    print(f"  Elapsed time    : {C.CYAN}{summary['elapsed_time']}{C.RESET}")
    print(f"  Products scraped: {C.BRIGHT_GREEN}{summary['products']['scraped']}{C.RESET}")
    print(f"  Price changes   : {C.BRIGHT_YELLOW}{summary['activities']['price_changes']}{C.RESET}")
    print(f"  Errors          : {C.BRIGHT_RED}{summary['activities']['errors']}{C.RESET}")
    print()
    print(f"  {C.BRIGHT_GREEN}✓{C.RESET} Report saved to {C.BOLD}{filename}{C.RESET}")
    print()

    # Price alerts
    alerts = tracker.get_price_alerts()
    if alerts:
        print(f"  {C.BOLD}Price Change Alerts ({len(alerts)}){C.RESET}")
        print(f"  {'─'*58}")
        for alert in alerts:
            print(f"  {C.CYAN}{alert['asin']}{C.RESET} : {C.GREEN}₹{alert['current_price']}{C.RESET} "
                  f"(low:{C.GREEN}₹{alert['lowest_price']}{C.RESET} "
                  f"high:{C.YELLOW}₹{alert['highest_price']}{C.RESET}) "
                  f"changes:{C.BOLD}{alert['changes']}{C.RESET}")
        print()


def cmd_interactive(args):
    """Launch interactive menu"""
    from log_viewer import LogViewer
    config = Config()

    while True:
        banner()
        print(f"  {C.BOLD}Main Menu{C.RESET}")
        print(f"  {C.DIM}{'─'*60}{C.RESET}")
        print()
        print(f"  {C.BRIGHT_CYAN}SCRAPING{C.RESET}")
        print(f"    1.  Run scrape (target query)")
        print(f"    2.  Run scrape with decoy")
        print(f"    3.  Scrape custom query")
        print(f"    4.  Start continuous monitoring")
        print()
        print(f"  {C.BRIGHT_MAGENTA}ANALYSIS{C.RESET}")
        print(f"    5.  Run AI analysis (ASIN)")
        print()
        print(f"  {C.BRIGHT_GREEN}STATUS & REPORTS{C.RESET}")
        print(f"    6.  View session status")
        print(f"    7.  Export report")
        print(f"    8.  View price alerts")
        print()
        print(f"  {C.BRIGHT_YELLOW}LOGS{C.RESET}")
        print(f"    9.  View activity log")
        print(f"    10. View errors only")
        print(f"    11. Search logs")
        print(f"    12. View scraper log")
        print()
        print(f"  {C.BRIGHT_BLUE}CONFIGURATION{C.RESET}")
        print(f"    13. Show configuration")
        print(f"    14. List queries & ASINs")
        print(f"    15. Add target query")
        print(f"    16. Add decoy query")
        print(f"    17. Add monitored ASIN")
        print(f"    18. Set scrape interval")
        print()
        print(f"    {C.BOLD}0.  Exit{C.RESET}")
        print()

        choice = input(f"  {C.BRIGHT_CYAN}Enter choice{C.RESET}: ").strip()

        if choice == '0':
            print(f"\n  {C.DIM}Goodbye!{C.RESET}\n")
            break

        elif choice == '1':
            _cmd_scrape_interactive()
        elif choice == '2':
            class Args:
                query = None
                decoy = True
            cmd_scrape(Args())
        elif choice == '3':
            query = input(f"  Query: ").strip()
            if query:
                class Args:
                    query = query
                    decoy = False
                cmd_scrape(Args())
        elif choice == '4':
            class Args:
                interval = None
            cmd_monitor(Args())
        elif choice == '5':
            asin = input(f"  ASIN: ").strip()
            if asin:
                class Args:
                    asin = asin
                cmd_analyze(Args())
        elif choice == '6':
            class Args:
                pass
            cmd_status(Args())
        elif choice == '7':
            class Args:
                output = None
            cmd_report(Args())
        elif choice == '8':
            tracker = stats_tracker
            alerts = tracker.get_price_alerts()
            if alerts:
                print(f"\n  {C.BOLD}Price Change Alerts{C.RESET}")
                for a in alerts:
                    print(f"  {C.CYAN}{a['asin']}{C.RESET}: ₹{a['current_price']} "
                          f"(changes: {a['changes']})")
            else:
                print(f"\n  {C.YELLOW}No price changes detected.{C.RESET}")
            print()
        elif choice == '9':
            viewer = LogViewer()
            viewer.view_activity_log()
        elif choice == '10':
            viewer = LogViewer()
            viewer.view_errors()
        elif choice == '11':
            query = input(f"  Search: ").strip()
            if query:
                viewer = LogViewer()
                viewer.search(query)
        elif choice == '12':
            viewer = LogViewer()
            viewer.view_bot_log()
        elif choice == '13':
            class Args:
                show = True
                list_queries = False
                add_query = None
                add_decoy = None
                add_asin = None
                set_interval = None
                set_jitter = None
            cmd_config(Args())
        elif choice == '14':
            class Args:
                show = False
                list_queries = True
                add_query = None
                add_decoy = None
                add_asin = None
                set_interval = None
                set_jitter = None
            cmd_config(Args())
        elif choice == '15':
            q = input(f"  Query to add: ").strip()
            if q:
                _env_edit('TARGET_QUERIES', q)
        elif choice == '16':
            q = input(f"  Decoy query to add: ").strip()
            if q:
                _env_edit('DECOY_QUERIES', q)
        elif choice == '17':
            a = input(f"  ASIN to add: ").strip()
            if a:
                _env_edit('MONITORED_ASINS', a)
        elif choice == '18':
            val = input(f"  Interval (hours): ").strip()
            if val:
                try:
                    _env_set('SCRAPE_INTERVAL_HOURS', val)
                except ValueError:
                    print(f"  {C.BRIGHT_RED}Invalid number{C.RESET}")
        else:
            print(f"  {C.BRIGHT_RED}Invalid choice{C.RESET}")

        input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")


def _cmd_scrape_interactive():
    """Run scrape with query selection from config"""
    config = Config()
    if not config.TARGET_QUERIES:
        print(f"  {C.BRIGHT_RED}No target queries configured.{C.RESET}")
        return

    print(f"\n  {C.BOLD}Select query:{C.RESET}")
    for i, q in enumerate(config.TARGET_QUERIES, 1):
        print(f"    {i}. {q}")
    print(f"    {len(config.TARGET_QUERIES)+1}. Custom query")

    choice = input(f"  Choice: ").strip()
    try:
        idx = int(choice) - 1
        if idx < len(config.TARGET_QUERIES):
            query = config.TARGET_QUERIES[idx]
        else:
            query = input(f"  Custom query: ").strip()
            if not query:
                return
    except ValueError:
        query = config.TARGET_QUERIES[0]

    class Args:
        query = query
        decoy = False
    cmd_scrape(Args())


# ==================== Argument Parser ====================

def build_parser():
    """Build the argument parser"""
    parser = argparse.ArgumentParser(
        prog='amazon-monitor',
        description='Amazon Price Monitor CLI - Control scraping, analysis, and monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py scrape                          Scrape default query
  python cli.py scrape "SKF 6204 bearing"       Scrape custom query
  python cli.py scrape --decoy                  Scrape with decoy queries
  python cli.py monitor                         Start continuous monitoring
  python cli.py monitor --interval 4            Monitor every 4 hours
  python cli.py analyze B09XYZ1234              AI analysis for ASIN
  python cli.py status                          Show session status
  python cli.py logs --errors                   View errors only
  python cli.py logs --prices                   View price changes
  python cli.py logs --search "B09XYZ"          Search logs
  python cli.py config --show                   Show full configuration
  python cli.py config --list-queries           List all queries and ASINs
  python cli.py config --add-query "NSK 6206"   Add a target query
  python cli.py config --add-asin B09XYZ1234    Add a monitored ASIN
  python cli.py config --set-interval 4         Set interval to 4 hours
  python cli.py report                          Export session report
  python cli.py interactive                     Launch interactive menu
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # scrape
    p_scrape = subparsers.add_parser('scrape', help='Run a single scrape session')
    p_scrape.add_argument('query', nargs='?', help='Search query (default: from config)')
    p_scrape.add_argument('--decoy', action='store_true', help='Include decoy queries')

    # monitor
    p_monitor = subparsers.add_parser('monitor', help='Start continuous monitoring')
    p_monitor.add_argument('--interval', type=float, help='Hours between sessions')

    # analyze
    p_analyze = subparsers.add_parser('analyze', help='Run AI analysis for an ASIN')
    p_analyze.add_argument('asin', nargs='?', help='ASIN to analyze')

    # status
    subparsers.add_parser('status', help='Show current session status')

    # logs
    p_logs = subparsers.add_parser('logs', help='View and filter logs')
    p_logs.add_argument('--errors', action='store_true', help='Show errors only')
    p_logs.add_argument('--prices', action='store_true', help='Show price changes')
    p_logs.add_argument('--search', type=str, help='Search logs for text')
    p_logs.add_argument('--type', type=str, help='Filter by activity type (SCRAPE, ANALYSIS, etc.)')
    p_logs.add_argument('--scraper', action='store_true', help='View scraper log')
    p_logs.add_argument('--level', type=str, default='INFO', help='Log level (DEBUG/INFO/WARNING/ERROR)')
    p_logs.add_argument('--limit', '-n', type=int, default=50, help='Number of entries')
    p_logs.add_argument('--tail', action='store_true', help='Tail activity log')

    # config
    p_config = subparsers.add_parser('config', help='View/edit configuration')
    p_config.add_argument('--show', action='store_true', help='Show full configuration')
    p_config.add_argument('--list-queries', action='store_true', help='List all queries and ASINs')
    p_config.add_argument('--add-query', type=str, help='Add a target query')
    p_config.add_argument('--add-decoy', type=str, help='Add a decoy query')
    p_config.add_argument('--add-asin', type=str, help='Add a monitored ASIN')
    p_config.add_argument('--set-interval', type=float, help='Set scrape interval (hours)')
    p_config.add_argument('--set-jitter', type=float, help='Set schedule jitter (minutes)')

    # report
    p_report = subparsers.add_parser('report', help='Export session report')
    p_report.add_argument('--output', '-o', type=str, help='Output filename')

    # interactive
    subparsers.add_parser('interactive', help='Launch interactive menu')

    return parser


# ==================== Entry Point ====================

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print()
        print(f"  {C.DIM}Quick start:{C.RESET}")
        print(f"    {C.CYAN}python cli.py scrape{C.RESET}          Run a scrape")
        print(f"    {C.CYAN}python cli.py status{C.RESET}          Check status")
        print(f"    {C.CYAN}python cli.py interactive{C.RESET}     Interactive menu")
        print()
        return

    handlers = {
        'scrape': cmd_scrape,
        'monitor': cmd_monitor,
        'analyze': cmd_analyze,
        'status': cmd_status,
        'logs': cmd_logs,
        'config': cmd_config,
        'report': cmd_report,
        'interactive': cmd_interactive,
    }

    handler = handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print(f"\n  {C.YELLOW}Interrupted{C.RESET}\n")
        except Exception as e:
            print(f"\n  {C.BRIGHT_RED}Error: {e}{C.RESET}\n")
            if os.getenv('DEBUG'):
                import traceback
                traceback.print_exc()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
