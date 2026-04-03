# Amazon Price Monitoring System

A Scrapy-based price monitor with **human-like browsing patterns** to avoid detection.

## Features
- **Human-like timing**: Log-normal distributed delays, hesitation pauses, randomized request patterns
- **Scrape pattern randomization**: Decoy queries, shuffled query order, variable timing
- **Proxy rotation**: Rotates proxies and user-agents per request
- **AI-powered analysis**: Ollama local LLM analyzes price trends and gives recommendations
- **Streamlit dashboard**: Interactive price charts, seller tables, on-demand AI analysis
- **Enhanced logging**: Activity tracking, error monitoring, session reports

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Install Ollama and pull the model:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull hf.co/quelmap/Lightning-4b-GGUF-short-ctx:Q4_K_M
   ```
3. Configure `.env` with your MongoDB URI, proxy list, and target queries.
4. Start MongoDB locally or use a cloud instance.

## Running
- **CLI (recommended):** `python cli.py interactive` — full interactive menu
- **Scraper only:** `scrapy crawl amazon -a query="SKF bearing 6205"`
- **CLI scrape:** `python cli.py scrape` or `python cli.py scrape "custom query"`
- **CLI monitor:** `python cli.py monitor` or `python cli.py monitor --interval 4`
- **Enhanced scheduler:** `python orchestrator.py --mode scheduled`
- **Single session:** `python orchestrator.py --mode once`
- **Direct ASIN checks:** `python orchestrator.py --mode direct-asin`
- **Legacy scheduler:** `python run_spider.py`
- **Dashboard:** `streamlit run dashboard/app.py`
- **Manual analysis:** `python cli.py analyze <ASIN>` or `python -m analysis.analyze <ASIN>`

## CLI Commands

The CLI (`python cli.py`) is the primary control interface:

```bash
# Scraping
python cli.py scrape                          # Scrape default query
python cli.py scrape "SKF 6204 bearing"       # Custom query
python cli.py scrape --decoy                  # Include decoy queries
python cli.py monitor                         # Continuous monitoring
python cli.py monitor --interval 4            # Every 4 hours

# Analysis
python cli.py analyze B09XYZ1234              # AI analysis

# Status & Reports
python cli.py status                          # Session status
python cli.py report                          # Export report
python cli.py report -o my_report.txt         # Custom filename

# Logs
python cli.py logs                            # Recent activity
python cli.py logs --errors                   # Errors only
python cli.py logs --prices                   # Price changes
python cli.py logs --search "B09XYZ"          # Search logs
python cli.py logs --type SCRAPE              # Filter by type
python cli.py logs --scraper                  # Scraper log

# Configuration
python cli.py config --show                   # Full config
python cli.py config --list-queries           # List queries/ASINs
python cli.py config --add-query "NSK 6206"   # Add target query
python cli.py config --add-decoy "FAG 6205"   # Add decoy query
python cli.py config --add-asin B09XYZ1234    # Add monitored ASIN
python cli.py config --set-interval 4         # Set interval
python cli.py config --set-jitter 20          # Set jitter

# Interactive
python cli.py interactive                     # Full menu interface
```

## Monitoring
- **Log viewer:** `python log_viewer.py` (interactive menu)
- **View errors:** `python log_viewer.py errors`
- **View price changes:** `python log_viewer.py prices`
- **Search logs:** `python log_viewer.py search <query>`

## Human-like Behavior
The scraper mimics human browsing patterns:
- **Log-normal distributed delays** between requests (not fixed intervals)
- **Hesitation pauses** (30% chance of extra pause before actions)
- **Decoy queries** between target queries to appear more natural
- **Session start delays** (5-15 seconds, simulates opening browser)
- **Variable reading times** per page type (search: 3-10s, product: 8-25s, offers: 15-45s)
- **Schedule jitter** (±30 minutes on the 6-hour interval)

## Configuration
All settings are in `.env`. Key parameters:
- `TARGET_QUERIES`: Comma-separated search queries to monitor
- `DECOY_QUERIES`: Unrelated queries inserted randomly
- `SCRAPE_INTERVAL_HOURS`: Base interval between sessions
- `SCHEDULE_JITTER_MINUTES`: Random variation added to schedule
- `HESITATION_PROBABILITY`: Chance of extra pause (0.0-1.0)
- `READING_TIME_*_MIN/MAX`: Time ranges per page type
