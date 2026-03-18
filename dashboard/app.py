import streamlit as st
import pymongo
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.getenv('MONGO_DB', 'amazon_pricing')

@st.cache_data(ttl=300)
def load_data(asin=None, days=30):
    client = pymongo.MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    query = {}
    if asin:
        query['asin'] = asin
    # Filter by last N days
    cutoff = datetime.now() - timedelta(days=days)
    query['scrape_date'] = {'$gte': cutoff}
    data = list(db.products.find(query, {'_id': 0}).sort('scrape_date', -1))
    client.close()
    return pd.DataFrame(data)

st.set_page_config(layout="wide")
st.title("Amazon Bearing Price Monitor")

# Sidebar filters
st.sidebar.header("Filters")
all_asins = load_data()['asin'].unique() if not load_data().empty else []
selected_asin = st.sidebar.selectbox("Select ASIN", all_asins)
days = st.sidebar.slider("Days of history", 1, 90, 30)

df = load_data(selected_asin, days)

if df.empty:
    st.warning("No data for selected filters.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest Price", f"₹{df.iloc[0]['price']}")
    col2.metric("Avg Price (7d)", f"₹{df['price'].tail(7).mean():.2f}")
    col3.metric("Default Seller", df.iloc[0]['default_seller'])

    # Price trend chart
    fig = px.line(df, x='scrape_date', y='price', title='Price History', markers=True)
    st.plotly_chart(fig, use_container_width=True)

    # Seller distribution
    st.subheader("Seller List (Latest)")
    latest_sellers = df.iloc[0]['seller_list']
    if latest_sellers:
        sellers_df = pd.DataFrame(latest_sellers)
        st.dataframe(sellers_df)

    # Analysis from Ollama (optional, can be triggered)
    if st.button("Run AI Analysis"):
        from analysis.analyze import analyze_asin
        with st.spinner("Analyzing..."):
            rec = analyze_asin(selected_asin)
        st.info(rec)
