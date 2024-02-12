from PyQt6.QtWidgets import QTableWidgetItem
from util.aogetutil import dehumanized_eta


class EtaWidgetItem(QTableWidgetItem):
    """Table widget for displaying the ETA for jobs. Sortable."""

    def __lt__(self, other):
        """Sort the table by the original size which in humanized form."""
        self_eta_text = self.__strip_text_from_rate(self.text())
        other_eta_text = self.__strip_text_from_rate(other.text())
        self_eta_seconds = dehumanized_eta(self_eta_text)
        other_eta_seconds = dehumanized_eta(other_eta_text)
        return self_eta_seconds < other_eta_seconds

    def __strip_text_from_rate(self, rate_text):
        """Strip the text from the rate."""
        if len(rate_text) > 3 and rate_text.endswith("/s"):
            rate_text = rate_text[:-2]
        return rate_text
