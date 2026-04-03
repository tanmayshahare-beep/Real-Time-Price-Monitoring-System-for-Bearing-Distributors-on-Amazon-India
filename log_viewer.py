"""
Log Viewer for Amazon Price Monitor - View and filter scrape logs.
Provides colored output, filtering by type, search, and error-only views.
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional


class LogViewer:
    """View and filter Amazon Price Monitor logs"""

    def __init__(self):
        self.activity_log = Path('activity.log')
        self.bot_log = Path('amazon_scraper.log')
        self.stats_file = Path('bot_stats.json')

    def colors(self):
        """ANSI color codes"""
        return {
            'RESET': '\033[0m',
            'RED': '\033[31m',
            'GREEN': '\033[32m',
            'YELLOW': '\033[33m',
            'BLUE': '\033[34m',
            'MAGENTA': '\033[35m',
            'CYAN': '\033[36m',
            'BRIGHT_RED': '\033[91m',
            'BRIGHT_GREEN': '\033[92m',
            'BRIGHT_YELLOW': '\033[93m',
            'BRIGHT_BLUE': '\033[94m',
            'BRIGHT_MAGENTA': '\033[95m',
            'BRIGHT_CYAN': '\033[96m',
        }

    def view_activity_log(self, limit: int = 50, filter_type: Optional[str] = None):
        """
        View activity log.

        Args:
            limit: Number of entries to show
            filter_type: Filter by activity type (SCRAPE, ANALYSIS, SCHEDULE, ERROR, etc.)
        """
        c = self.colors()

        if not self.activity_log.exists():
            print(f"{c['YELLOW']}No activity log found.{c['RESET']}")
            return

        print(f"\n{c['BRIGHT_CYAN']}{'='*60}{c['RESET']}")
        print(f"{c['BRIGHT_CYAN']}ACTIVITY LOG - Amazon Price Monitor{c['RESET']}")
        print(f"{c['BRIGHT_CYAN']}{'='*60}{c['RESET']}\n")

        with open(self.activity_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        filtered_lines = lines
        if filter_type:
            filtered_lines = [l for l in lines if f'[{filter_type}]' in l]

        for line in filtered_lines[-limit:]:
            line = line.strip()

            # Color by status
            if '[SUCCESS]' in line:
                line = line.replace('[SUCCESS]', f"{c['BRIGHT_GREEN']}[SUCCESS]{c['RESET']}")
            elif '[FAILED]' in line:
                line = line.replace('[FAILED]', f"{c['BRIGHT_RED']}[FAILED]{c['RESET']}")
            elif '[OK]' in line:
                line = line.replace('[OK]', f"{c['GREEN']}[OK]{c['RESET']}")
            elif '[SKIPPED]' in line:
                line = line.replace('[SKIPPED]', f"{c['YELLOW']}[SKIPPED]{c['RESET']}")

            # Color by category
            if '[SCRAPE]' in line:
                line = line.replace('[SCRAPE]', f"{c['BRIGHT_CYAN']}[SCRAPE]{c['RESET']}")
            elif '[ANALYSIS]' in line:
                line = line.replace('[ANALYSIS]', f"{c['BRIGHT_MAGENTA']}[ANALYSIS]{c['RESET']}")
            elif '[SCHEDULE]' in line:
                line = line.replace('[SCHEDULE]', f"{c['BRIGHT_BLUE']}[SCHEDULE]{c['RESET']}")
            elif '[ERROR]' in line:
                line = line.replace('[ERROR]', f"{c['BRIGHT_RED']}[ERROR]{c['RESET']}")
            elif '[BLOCKED]' in line:
                line = line.replace('[BLOCKED]', f"{c['BRIGHT_RED']}[BLOCKED]{c['RESET']}")
            elif '[PROXY]' in line:
                line = line.replace('[PROXY]', f"{c['CYAN']}[PROXY]{c['RESET']}")

            print(line)

        print(f"\n{c['DIM']}Showing {min(limit, len(filtered_lines))} of {len(filtered_lines)} entries{c['RESET']}")

    def view_bot_log(self, limit: int = 50, level: str = 'INFO'):
        """
        View bot log file.

        Args:
            limit: Number of lines to show
            level: Minimum log level to show
        """
        c = self.colors()

        if not self.bot_log.exists():
            print(f"{c['YELLOW']}No bot log found.{c['RESET']}")
            return

        print(f"\n{c['BRIGHT_CYAN']}{'='*60}{c['RESET']}")
        print(f"{c['BRIGHT_CYAN']}SCRAPER LOG ({level}+){c['RESET']}")
        print(f"{c['BRIGHT_CYAN']}{'='*60}{c['RESET']}\n")

        levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        min_level = levels.index(level) if level in levels else 1

        with open(self.bot_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        shown = 0
        for line in lines[-limit*2:]:
            line = line.strip()

            # Check log level
            show = False
            for i, lvl in enumerate(levels):
                if lvl in line and i >= min_level:
                    show = True
                    break

            if show:
                # Color by level
                if 'DEBUG' in line:
                    line = line.replace('DEBUG', f"{c['CYAN']}DEBUG{c['RESET']}")
                elif 'INFO' in line:
                    line = line.replace('INFO', f"{c['GREEN']}INFO{c['RESET']}")
                elif 'WARNING' in line:
                    line = line.replace('WARNING', f"{c['YELLOW']}WARNING{c['RESET']}")
                elif 'ERROR' in line:
                    line = line.replace('ERROR', f"{c['RED']}ERROR{c['RESET']}")
                elif 'CRITICAL' in line:
                    line = line.replace('CRITICAL', f"{c['RED']}CRITICAL{c['RESET']}")

                print(line)
                shown += 1

                if shown >= limit:
                    break

        print(f"\n{c['DIM']}Showing {shown} entries{c['RESET']}")

    def view_errors(self, limit: int = 20):
        """View only error entries"""
        c = self.colors()

        print(f"\n{c['BRIGHT_RED']}{'='*60}{c['RESET']}")
        print(f"{c['BRIGHT_RED']}ERRORS ONLY{c['RESET']}")
        print(f"{c['BRIGHT_RED']}{'='*60}{c['RESET']}\n")

        # Check activity log
        if self.activity_log.exists():
            with open(self.activity_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            errors = [l for l in lines if '[FAILED]' in l or '[ERROR]' in l or '[BLOCKED]' in l]

            if errors:
                print(f"{c['BRIGHT_YELLOW']}From Activity Log:{c['RESET']}")
                for line in errors[-limit:]:
                    line = line.strip()
                    line = line.replace('[FAILED]', f"{c['BRIGHT_RED']}[FAILED]{c['RESET']}")
                    line = line.replace('[ERROR]', f"{c['BRIGHT_RED']}[ERROR]{c['RESET']}")
                    line = line.replace('[BLOCKED]', f"{c['BRIGHT_RED']}[BLOCKED]{c['RESET']}")
                    print(line)
                print()

        # Check bot log
        if self.bot_log.exists():
            with open(self.bot_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            errors = [l for l in lines if 'ERROR' in l or 'CRITICAL' in l]

            if errors:
                print(f"{c['BRIGHT_YELLOW']}From Scraper Log:{c['RESET']}")
                for line in errors[-limit:]:
                    line = line.strip()
                    line = line.replace('ERROR', f"{c['BRIGHT_RED']}ERROR{c['RESET']}")
                    print(line)

    def view_price_alerts(self, limit: int = 20):
        """View price change entries"""
        c = self.colors()

        print(f"\n{c['BRIGHT_GREEN']}{'='*60}{c['RESET']}")
        print(f"{c['BRIGHT_GREEN']}PRICE CHANGES{c['RESET']}")
        print(f"{c['BRIGHT_GREEN']}{'='*60}{c['RESET']}\n")

        if not self.activity_log.exists():
            print(f"{c['YELLOW']}No activity log found.{c['RESET']}")
            return

        with open(self.activity_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find entries with price info
        price_lines = [l for l in lines if 'Price:' in l and 'SCRAPE' in l]

        if price_lines:
            for line in price_lines[-limit:]:
                line = line.strip()
                if '[SUCCESS]' in line:
                    line = line.replace('[SUCCESS]', f"{c['BRIGHT_GREEN']}[SUCCESS]{c['RESET']}")
                if '[SCRAPE]' in line:
                    line = line.replace('[SCRAPE]', f"{c['BRIGHT_CYAN']}[SCRAPE]{c['RESET']}")
                print(line)
        else:
            print(f"{c['YELLOW']}No price change entries found.{c['RESET']}")

    def tail(self, filename: str, lines: int = 20):
        """
        Tail a log file (show last N lines).

        Args:
            filename: Log file to tail
            lines: Number of lines to show
        """
        c = self.colors()
        path = Path(filename)

        if not path.exists():
            print(f"{c['YELLOW']}File not found: {filename}{c['RESET']}")
            return

        print(f"\n{c['BRIGHT_CYAN']}Last {lines} lines of {filename}{c['RESET']}\n")

        with open(path, 'r', encoding='utf-8') as f:
            file_lines = f.readlines()

        for line in file_lines[-lines:]:
            print(line.strip())

    def search(self, query: str, case_sensitive: bool = False):
        """
        Search logs for a query.

        Args:
            query: Search query (ASIN, product name, error message)
            case_sensitive: Whether search is case-sensitive
        """
        c = self.colors()

        print(f"\n{c['BRIGHT_CYAN']}Searching for: \"{query}\"{c['RESET']}\n")

        results = []

        # Search activity log
        if self.activity_log.exists():
            with open(self.activity_log, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if case_sensitive:
                        if query in line:
                            results.append((f'activity.log:{i}', line.strip()))
                    else:
                        if query.lower() in line.lower():
                            results.append((f'activity.log:{i}', line.strip()))

        # Search bot log
        if self.bot_log.exists():
            with open(self.bot_log, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if case_sensitive:
                        if query in line:
                            results.append((f'amazon_scraper.log:{i}', line.strip()))
                    else:
                        if query.lower() in line.lower():
                            results.append((f'amazon_scraper.log:{i}', line.strip()))

        if results:
            print(f"Found {len(results)} matches:\n")
            for location, line in results[:50]:
                print(f"{c['YELLOW']}{location}{c['RESET']}: {line}")

            if len(results) > 50:
                print(f"\n{c['DIM']}... and {len(results) - 50} more results{c['RESET']}")
        else:
            print(f"{c['YELLOW']}No matches found.{c['RESET']}")

    def show_menu(self):
        """Show interactive menu"""
        c = self.colors()

        while True:
            print(f"\n{c['BRIGHT_CYAN']}{'='*60}{c['RESET']}")
            print(f"{c['BRIGHT_CYAN']}AMAZON PRICE MONITOR - LOG VIEWER{c['RESET']}")
            print(f"{c['BRIGHT_CYAN']}{'='*60}{c['RESET']}")
            print()
            print("  1. View Activity Log (last 50 entries)")
            print("  2. View Scraper Log (last 50 entries)")
            print("  3. View Errors Only")
            print("  4. View Price Changes")
            print("  5. Search Logs")
            print("  6. View Activity Log by Type")
            print("  7. Tail Log File")
            print("  8. Exit")
            print()

            choice = input("Enter choice (1-8): ").strip()

            if choice == '1':
                self.view_activity_log()
            elif choice == '2':
                level = input("Log level (DEBUG/INFO/WARNING/ERROR) [INFO]: ").strip().upper()
                if not level:
                    level = 'INFO'
                self.view_bot_log(limit=50, level=level)
            elif choice == '3':
                self.view_errors()
            elif choice == '4':
                self.view_price_alerts()
            elif choice == '5':
                query = input("Search query (ASIN, product, error): ").strip()
                if query:
                    self.search(query)
            elif choice == '6':
                print("\nActivity types: SCRAPE, ANALYSIS, SCHEDULE, ERROR, BLOCKED, PROXY")
                act_type = input("Filter by type: ").strip().upper()
                if act_type:
                    self.view_activity_log(filter_type=act_type)
            elif choice == '7':
                filename = input("Log file (activity.log/amazon_scraper.log): ").strip()
                if filename:
                    lines = input("Number of lines [20]: ").strip()
                    lines = int(lines) if lines else 20
                    self.tail(filename, lines)
            elif choice == '8':
                break
            else:
                print(f"{c['YELLOW']}Invalid choice.{c['RESET']}")

            input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    import sys

    viewer = LogViewer()

    # Command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == 'activity':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            filter_type = sys.argv[3].upper() if len(sys.argv) > 3 else None
            viewer.view_activity_log(limit, filter_type)
        elif command == 'scraper':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            level = sys.argv[3].upper() if len(sys.argv) > 3 else 'INFO'
            viewer.view_bot_log(limit, level)
        elif command == 'errors':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            viewer.view_errors(limit)
        elif command == 'prices':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            viewer.view_price_alerts(limit)
        elif command == 'search':
            query = sys.argv[2] if len(sys.argv) > 2 else ''
            if query:
                viewer.search(query)
        elif command == 'tail':
            filename = sys.argv[2] if len(sys.argv) > 2 else 'activity.log'
            lines = int(sys.argv[3]) if len(sys.argv) > 3 else 20
            viewer.tail(filename, lines)
        else:
            print(f"Unknown command: {command}")
    else:
        # Interactive menu
        viewer.show_menu()


if __name__ == '__main__':
    main()
