from PyQt6.QtWidgets import QTableWidgetItem
from util.aogetutil import dehumanized_filesize


class RateWidgetItem(QTableWidgetItem):
    """Table widget for displaying the download rate of the files. Sortable."""

    def __lt__(self, other):
        """Sort the table by the original size which in humanized form."""
        self_size_text = self.__strip_text_from_rate(self.text())
        other_size_text = self.__strip_text_from_rate(other.text())
        self_size_bytes = dehumanized_filesize(self_size_text)
        other_size_bytes = dehumanized_filesize(other_size_text)
        return self_size_bytes < other_size_bytes

    def __strip_text_from_rate(self, rate_text):
        """Strip the text from the rate."""
        if len(rate_text) > 3 and rate_text.endswith("/s"):
            rate_text = rate_text[:-2]
        return rate_text
