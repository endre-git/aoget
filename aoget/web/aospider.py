import scrapy
from pathlib import Path


class AoSpider(scrapy.Spider):
    """Scrapy spider to parse the links from a webpage. It will extract the title of the page and
    the links to downloadable files. It will group the files by extension fore downstream
    use."""
    extension_counts = {}
    files_by_extension = {}

    def __init__(self, *args, **kwargs):
        self.start_urls = [kwargs.get("start_url")]
        self.base_url = kwargs.get("start_url")
        self.ao_page = kwargs.get("ao_page")
        self.name = kwargs.get("name")
        self.allowed_domains = [kwargs.get("allowed_domains")]
        super(AoSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        hxs = scrapy.Selector(response)
        self.extract_title(response)
        # extract all links from page
        for url in hxs.xpath('*//a/@href').extract():
            # make it a valid url
            if not (url.startswith('http://') or url.startswith('https://')):
                url = self.base_url + "/" + url
            # process the url
            self.handle(url)
            # recusively parse each url
            ##yield scrapy.http.Request(url=url, callback=self.parse)

    def extract_title(self, response):
        title = response.xpath('//title/text()').extract_first()
        self.ao_page.page_title = title

    def handle(self, url):
        if self.ao_page is not None:
            extension = Path(url).suffix
            if not url.endswith('/') and '?' not in extension and '&' not in extension:
                self.ao_page.add_file_by_extension(extension, url)
