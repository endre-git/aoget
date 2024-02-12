from PyQt6.QtWidgets import QTableWidgetItem
from util.aogetutil import dehumanized_priority


class PriorityWidgetItem(QTableWidgetItem):
    """Table widget for displaying the download rate of the files. Sortable."""

    def __lt__(self, other):
        """Sort the table by the original size which in humanized form."""
        self_prio = dehumanized_priority(self.text())
        other_prio = dehumanized_priority(other.text())
        return self_prio < other_prio
