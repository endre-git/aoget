from PyQt6.QtWidgets import QTableWidgetItem
from model.file_model import FileModel


class FileStatusWidgetItem(QTableWidgetItem):
    """Table widget for displaying the download rate of the files. Sortable."""

    def __lt__(self, other):
        """Sort the table by the original size which in humanized form."""
        self_int = FileStatusWidgetItem.__status_to_int(self.text())
        other_int = FileStatusWidgetItem.__status_to_int(other.text())
        return self_int < other_int

    def __status_to_int(status: str):
        """Convert the status to an integer."""
        if status == FileModel.STATUS_COMPLETED:
            return 1
        if status == FileModel.STATUS_DOWNLOADING:
            return 2
        elif status == FileModel.STATUS_QUEUED:
            return 3
        elif status == FileModel.STATUS_STOPPING:
            return 4
        elif status == FileModel.STATUS_STOPPED:
            return 5
        elif status == FileModel.STATUS_NEW:
            return 6
        elif status == FileModel.STATUS_INVALID:
            return 7
        else:
            return -1
