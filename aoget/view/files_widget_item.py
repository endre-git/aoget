from PyQt6.QtWidgets import QTableWidgetItem


class FilesWidgetItem(QTableWidgetItem):
    """Table widget for displaying the number of completed / total files. Sortable."""

    def __lt__(self, other):
        """Sort the table based on the total file count."""
        self_files = self.text()
        if "/" in self_files:
            # text after the first "/"
            self_files = self_files.split("/")[1]
        other_files = other.text()
        if "/" in other_files:
            # text before the first "/"
            other_files = other_files.split("/")[1]
        return int(self_files) < int(other_files)
