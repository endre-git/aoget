import os
import logging

from scrapy.crawler import CrawlerProcess
from aospider import AoSpider
from aopage import AoPage

logger = logging.getLogger(__name__)

process = CrawlerProcess(
    settings={
        "FEEDS": {
            "items.json": {"format": "json"},
        },
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
        "HTTPCACHE_ENABLED": False,
    }
)

page_url = "https://archive.org/download/gamecubeusaredump"

ao_page = AoPage()
process.crawl(AoSpider,
              ao_page=ao_page,
              name="aoget",
              allowed_domains="archive.org",
              start_urls=[page_url])
process.start()  # the script will block here until the crawling is finished

logger.info("Files by extension: " + str(ao_page.extension_counts))
logger.info("7z files: " + str(ao_page.files_by_extension[".7z"]))
