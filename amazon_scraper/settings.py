import os
from dotenv import load_dotenv
load_dotenv()

BOT_NAME = 'amazon_scraper'

SPIDER_MODULES = ['amazon_scraper.spiders']
NEWSPIDER_MODULE = 'amazon_scraper.spiders'

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True

# Proxy and retry settings
PROXY_LIST = os.getenv('PROXY_LIST', '').split(',') if os.getenv('PROXY_LIST') else []
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 403, 429, 408]

DOWNLOADER_MIDDLEWARES = {
    'amazon_scraper.middlewares.RotatingProxyMiddleware': 350,
    'amazon_scraper.middlewares.CustomRetryMiddleware': 400,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 450,
}

ITEM_PIPELINES = {
    'amazon_scraper.pipelines.MongoPipeline': 300,
}

# MongoDB settings
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB = os.getenv('MONGO_DB', 'amazon_pricing')

# Logging
LOG_LEVEL = 'INFO'
