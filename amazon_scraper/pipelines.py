import pymongo
import datetime
from scrapy.utils.project import get_project_settings
from itemadapter import ItemAdapter

class MongoPipeline:
    def open_spider(self, spider):
        settings = get_project_settings()
        self.client = pymongo.MongoClient(settings['MONGO_URI'])
        self.db = self.client[settings['MONGO_DB']]
        # Ensure indexes for performance
        self.db.products.create_index([('asin', pymongo.ASCENDING), ('scrape_date', pymongo.ASCENDING)])

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        adapter['scrape_date'] = datetime.datetime.now()
        # Insert or replace the document for this ASIN and date (keep history)
        self.db.products.update_one(
            {'asin': adapter['asin'], 'scrape_date': adapter['scrape_date']},
            {'$set': dict(adapter)},
            upsert=True
        )
        return item
