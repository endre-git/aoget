from PyQt6.QtWidgets import QTableWidgetItem
from util.aogetutil import dehumanized_filesize


class SizeWidgetItem(QTableWidgetItem):
    """Table widget for displaying the on-disk size of the files. Sortable."""

    def __lt__(self, other):
        """Sort the table by the original size which in humanized form."""
        self_size_text = self.text()
        if self_size_text.startswith(">"):
            self_size_text = self_size_text[1:]
        other_size_text = other.text()
        if other_size_text.startswith(">"):
            other_size_text = other_size_text[1:]
        self_size_bytes = dehumanized_filesize(self_size_text)
        other_size_bytes = dehumanized_filesize(other_size_text)
        return self_size_bytes < other_size_bytes
