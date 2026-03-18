import pymongo
import datetime
import os
from dotenv import load_dotenv
from analysis.ollama_client import ask_ollama
import pandas as pd

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.getenv('MONGO_DB', 'amazon_pricing')

def get_recent_data(asin, days=7):
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    data = list(db.products.find(
        {'asin': asin, 'scrape_date': {'$gte': cutoff}},
        {'_id': 0, 'price': 1, 'default_seller': 1, 'scrape_date': 1, 'seller_list': 1}
    ).sort('scrape_date', 1))
    client.close()
    return data

def format_data_for_prompt(data):
    df = pd.DataFrame(data)
    # Basic stats
    if df.empty:
        return "No data available for this period."
    summary = f"Analyzed period: {df['scrape_date'].min()} to {df['scrape_date'].max()}\n"
    summary += f"Number of observations: {len(df)}\n"
    summary += f"Price range: ₹{df['price'].min()} - ₹{df['price'].max()}\n"
    summary += f"Average price: ₹{df['price'].mean():.2f}\n"
    summary += "Price changes by date:\n"
    for _, row in df.iterrows():
        summary += f"  {row['scrape_date'].strftime('%Y-%m-%d %H:%M')}: ₹{row['price']} (Seller: {row['default_seller']})\n"
    return summary

def analyze_asin(asin):
    data = get_recent_data(asin, days=7)
    summary = format_data_for_prompt(data)
    prompt = f"""
You are a pricing analyst for an industrial bearing distributor.
Based on the following 7-day price history for ASIN {asin}, provide a concise recommendation:

{summary}

Answer:
1. Current price trend (up/down/stable)
2. Who is the market leader (lowest price / most frequent default seller)?
3. Should we adjust our price? If yes, suggest a new price and explain why.
"""
    recommendation = ask_ollama(prompt)
    return recommendation

if __name__ == '__main__':
    # Example usage
    asin_to_analyze = 'B09XYZ1234'  # Replace with actual ASIN
    print(analyze_asin(asin_to_analyze))
