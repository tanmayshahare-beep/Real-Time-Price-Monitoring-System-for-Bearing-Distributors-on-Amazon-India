import scrapy

class ProductItem(scrapy.Item):
    asin = scrapy.Field()
    product_title = scrapy.Field()
    price = scrapy.Field()
    default_seller = scrapy.Field()
    seller_list = scrapy.Field()       # list of dicts: {'name': '...', 'price': ..., 'fba': bool}
    availability = scrapy.Field()
    scrape_date = scrapy.Field()
    url = scrapy.Field()
