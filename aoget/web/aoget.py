import os
import logging

logging.basicConfig(level=logging.CRITICAL)
import warnings

warnings.filterwarnings("ignore")

logging.getLogger("tldextract").propagate = False
logging.getLogger("urllib3").propagate = False
logging.getLogger("scrapy").propagate = False

from scrapy.crawler import CrawlerProcess
from aospider import AoSpider
from aopage import AoPage

URL_CACHE_REL_PATH = "app_settings/url_cache"
URL_HISTORY_REL_PATH = "app_settings/url_history.lst"
RESULTS_DIR = "app_logs"

process = CrawlerProcess(
    settings={
        "FEEDS": {
            "items.json": {"format": "json"},
        },
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "HTTPCACHE_ENABLED": False,
    }
)

ao_page = AoPage()
process.crawl(AoSpider, [base_url, ao_page])
process.start()  # the script will block here until the crawling is finished

logger.info("Files by extension: " + str(ao_page.extension_counts))
logger.info("7z files: " + str(ao_page.files_by_extension[".7z"]))
