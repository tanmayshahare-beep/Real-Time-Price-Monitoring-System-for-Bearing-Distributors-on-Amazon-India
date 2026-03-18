import subprocess
import schedule
import time
from analysis.analyze import analyze_asin

def run_spider():
    print("Starting spider...")
    subprocess.run(["scrapy", "crawl", "amazon", "-a", "query=SKF bearing 6205"])
    print("Spider finished.")

def run_analysis():
    # Example: analyze a known ASIN after each scrape
    asin = "B09XYZ1234"  # replace with logic to get latest ASINs
    rec = analyze_asin(asin)
    print(f"Analysis for {asin}:\n{rec}")

# Schedule every 6 hours
schedule.every(6).hours.do(run_spider)
# Run analysis 30 minutes after each scrape
schedule.every(6).hours.do(run_analysis).delay(30*60)

if __name__ == "__main__":
    print("Scheduler started. Will run spider every 6 hours.")
    while True:
        schedule.run_pending()
        time.sleep(60)
