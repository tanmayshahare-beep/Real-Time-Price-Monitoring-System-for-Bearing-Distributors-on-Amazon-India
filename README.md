# Amazon Price Monitoring System

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Install Ollama and pull the model:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull hf.co/quelmap/Lightning-4b-GGUF-short-ctx:Q4_K_M
   ```
3. Configure `.env` with your MongoDB URI and proxy list.
4. Start MongoDB locally or use a cloud instance.

## Running
- **Scraper only:** `scrapy crawl amazon -a query="SKF bearing 6205"`
- **Scheduler:** `python run_spider.py` (runs every 6 hours)
- **Dashboard:** `streamlit run dashboard/app.py`
- **Manual analysis:** `python -m analysis.analyze`
