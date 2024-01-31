
from typing import Any
import pickle


class CrawlerSubprocessArgs:
    def __init__(self, page_url) -> None:
        self.args["page_url"] = page_url

    def pickled(self) -> Any:
        """Pickle into a local file."""
        
    @classmethod
    def from_pickle(cls, filename: str) -> None:
        """Unpickle from a local file."""
        with open(filename, "rb") as f:
            args = pickle.load(f)


class CrawlerSubprocessResults:

    def __init__(self, url, html, error):
        self.url = url
        self.html = html
        self.error = error

