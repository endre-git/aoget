from scrapy.crawler import CrawlerProcess
from web.aopage import AoPage
from web.aospider import AoSpider
from util.aogetutil import is_valid_url
from crochet import setup, wait_for
from config.log_config import setup_logging


class PageCrawler():
    """Crawler for a page to collect all downloadable links. It creates a subprocess to run the
    spider, because Scrapy uses Twisted which has a peculiar event loop implementation, not playing
    nicely with anything but one-off crawler scripts."""

    def __init__(self, url):
        self.url = url
        self.ao_page = AoPage()
        setup()

    @wait_for(timeout=15.0)
    def run_spider(self):
        page_url = self.url
        if not is_valid_url(page_url):
            raise ValueError(
                "Invalid URL. Please enter a complete url, including http:// or https://"
            )

        crawler_runner = CrawlerProcess(
            settings={
                "FEEDS": {
                    "items.json": {"format": "json"},
                },
                "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
                "HTTPCACHE_ENABLED": False,
            }
        )
        
        allowed_domains = PageCrawler.__allowed_domains_of(page_url)
        result = crawler_runner.crawl(
            AoSpider,
            ao_page=self.ao_page,
            name="aoget-" + allowed_domains,
            allowed_domains=allowed_domains,
            start_url=page_url,
        )
        setup_logging()  # re-setup logging after scrapy has mucked with it
        return result

    def fetch_links(self) -> map:
        """Fetch the links from the given page url.
        Returns a map of extensions to file lists."""
        self.run_spider()
        return self.ao_page.files_by_extension

    def __allowed_domains_of(page_url):
        """Get the allowed domains of the given page url. By default this is the part of the url
        between the protocol and the first slash."""
        return page_url.split("//")[1].split("/")[0]
