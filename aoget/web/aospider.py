import scrapy
from web.aopage import AoPage
from pathlib import Path

class AoSpider(scrapy.Spider):

    extension_counts = {}
    files_by_extension = {}
    ao_page = AoPage()

    name = "archive.org"
    # limit the scope to stackoverflow
    allowed_domains = ["archive.org"]
    start_urls = [
        "https://archive.org/download/gamecubeusaredump",
    ]

    def parse(self, response):
        hxs = scrapy.Selector(response)
        # extract all links from page
        for url in hxs.xpath('*//a/@href').extract():
            # make it a valid url
            if not ( url.startswith('http://') or url.startswith('https://') ):
                url = "https://archive.org/download/" + url
            # process the url
            self.handle(url)
            # recusively parse each url
            ##yield scrapy.http.Request(url=url, callback=self.parse)

    def handle(self, url):
        if self.ao_page is not None:
            extension = Path(url).suffix
            if not url.endswith('/') and not '?' in extension and not '&' in extension:
                self.ao_page.add_file_by_extension(extension, url)

    def set_base_url(self, base_url):
        self.start_urls = [base_url]

    def set_ao_page(self, ao_page):
        self.ao_page = ao_page
