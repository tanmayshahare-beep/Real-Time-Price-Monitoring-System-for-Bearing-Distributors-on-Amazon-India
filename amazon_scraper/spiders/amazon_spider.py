import scrapy
from scrapy.http import HtmlResponse
from amazon_scraper.items import ProductItem
import re
import json
import time
import random
import math


class AmazonSpider(scrapy.Spider):
    name = 'amazon'
    allowed_domains = ['amazon.in']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_request_time = 0
        self._products_scraped = 0

    def _human_delay(self, min_sec=2.0, max_sec=8.0):
        """Apply human-like delay between requests."""
        delay = random.lognormvariate(math.log((min_sec + max_sec) / 2), 0.5)
        delay = max(min_sec, min(delay, max_sec))
        # 30% chance of hesitation
        if random.random() < 0.3:
            delay += random.uniform(1, 3)
        time.sleep(delay)
        return delay

    def start_requests(self):
        # You can pass search queries via command line: scrapy crawl amazon -a query="SKF bearing 6205"
        query = getattr(self, 'query', 'SKF bearing 6205')
        search_url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        yield scrapy.Request(search_url, callback=self.parse_search, meta={'handle_httpstatus_list': [403, 429]})

    def parse_search(self, response):
        """Extract product links from search results."""
        # Handle blocking
        if response.status in [403, 429]:
            self.logger.warning(f"Blocked on search page. Status: {response.status}")
            return

        # Human-like pause after page load (reading results)
        self._human_delay(3, 10)

        # Extract ASINs from data-component-id or links
        product_links = response.css('a.a-link-normal.s-no-outline::attr(href)').getall()
        for link in product_links:
            yield response.follow(link, callback=self.parse_product)

        # Pagination
        next_page = response.css('a.s-pagination-next::attr(href)').get()
        if next_page:
            # Human-like pause before clicking next
            self._human_delay(2, 5)
            yield response.follow(next_page, callback=self.parse_search)

    def parse_product(self, response):
        """Extract product details, including seller list from the 'See All Offers' page."""
        if response.status in [403, 429]:
            self.logger.warning(f"Blocked on product page: {response.url}")
            return

        # Human-like reading time on product page
        self._human_delay(8, 25)

        asin_match = re.search(r'/dp/([A-Z0-9]{10})', response.url)
        asin = asin_match.group(1) if asin_match else None
        if not asin:
            self.logger.warning(f"ASIN not found in URL: {response.url}")
            return

        # Basic product info
        title = response.css('span#productTitle::text').get()
        if title:
            title = title.strip()

        # Extract default buy box seller and price
        price = response.css('span.a-price-whole::text').get()
        if price:
            price = price.replace(',', '').strip()

        # Merchant name: sometimes in #merchant-info
        merchant_info = response.css('#merchant-info ::text').getall()
        default_seller = None
        for text in merchant_info:
            if 'sold by' in text.lower():
                default_seller = text.replace('Sold by', '').strip()
                break

        # Human-like pause before checking offers
        self._human_delay(5, 15)

        # Go to the "See All Offers" page to get full seller list
        offers_url = f"https://www.amazon.in/gp/offer-listing/{asin}"
        yield scrapy.Request(
            offers_url,
            callback=self.parse_offers,
            meta={'asin': asin, 'title': title, 'price': price, 'default_seller': default_seller, 'product_url': response.url}
        )

    def parse_offers(self, response):
        """Extract all sellers and their prices from the offers page."""
        if response.status in [403, 429]:
            self.logger.warning(f"Blocked on offers page: {response.url}")
            return

        # Human-like reading time on offers page
        self._human_delay(15, 45)

        asin = response.meta['asin']
        title = response.meta['title']
        default_price = response.meta['price']
        default_seller = response.meta['default_seller']
        product_url = response.meta['product_url']

        sellers = []
        # Each offer row
        offer_rows = response.css('div.a-row.a-spacing-mini.olpOffer')
        for row in offer_rows:
            seller_name = row.css('div.olpSellerName img::attr(alt)').get()
            if not seller_name:
                seller_name = row.css('div.olpSellerName a::text').get()
            if seller_name:
                seller_name = seller_name.strip()
            price_text = row.css('span.olpOfferPrice::text').get()
            if price_text:
                price = re.sub(r'[^\d.]', '', price_text)  # extract numeric
            else:
                price = None
            condition = row.css('span.olpCondition::text').get()
            if condition:
                condition = condition.strip()
            shipping = row.css('span.olpShippingPrice::text').get()
            if shipping:
                shipping = shipping.strip()

            sellers.append({
                'seller_name': seller_name,
                'price': price,
                'condition': condition,
                'shipping': shipping
            })

        self._products_scraped += 1
        self.logger.info(f"Scraped ASIN {asin}: {title[:50] if title else 'Unknown'} - ₹{default_price}")

        item = ProductItem()
        item['asin'] = asin
        item['product_title'] = title
        item['price'] = default_price
        item['default_seller'] = default_seller
        item['seller_list'] = sellers
        item['url'] = product_url
        # scrape_date will be added in pipeline
        yield item
