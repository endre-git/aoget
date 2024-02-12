from PyQt6.QtWidgets import QTableWidgetItem
from view.progress_bar_widget import ProgressBarWidget


class ProgressBarPlaceholderWidgetItem(QTableWidgetItem):
    """Table widget for displaying the ETA for jobs. Sortable."""

    def __lt__(self, other):
        """Sort the table by the original size which in humanized form."""
        if isinstance(other, ProgressBarPlaceholderWidgetItem):
            return False
        elif isinstance(other, ProgressBarWidget):
            return True
