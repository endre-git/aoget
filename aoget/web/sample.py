from page_crawler import PageCrawler

page_crawler = PageCrawler("https://www.artofzoo.com/videos/")
links1 = page_crawler.fetch_links()