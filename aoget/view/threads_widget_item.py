from PyQt6.QtWidgets import QTableWidgetItem


class ThreadsWidgetItem(QTableWidgetItem):
    """Table widget for displaying the active / allocated threads for jobs. Sortable."""

    def __lt__(self, other):
        """Sort the column based on active threads."""
        self_threads = self.text()
        if "/" in self_threads:
            # text before the first "/"
            self_threads = self_threads.split("/")[0]
        other_threads = other.text()
        if "/" in other_threads:
            # text before the first "/"
            other_threads = other_threads.split("/")[0]
        return int(self_threads) < int(other_threads)
