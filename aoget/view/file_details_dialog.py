from PyQt6.QtWidgets import QDialog
from PyQt6 import uic
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QHeaderView
from .file_details_controller import FileDetailsController
from util.aogetutil import human_timestamp_from


class FileDetailsDialog(QDialog):
    """File details dialog box showing the static properties and the full event log
    of a file."""

    def __init__(self, main_window_controller: any, job_name: str, file_name: str):
        """Create a new FileDetailsDialog."""
        super(FileDetailsDialog, self).__init__()
        uic.loadUi("aoget/qt/file_details.ui", self)
        self.setWindowTitle("Details of " + file_name)
        self.__setup_ui()
        self.controller = FileDetailsController(
            self, main_window_controller, job_name, file_name
        )
        self.__populate()

    def __setup_ui(self):
        """Setup the component post generation. This is called from the constructor."""
        # table headers of tblFileProperties are Property and Value
        self.tblFileProperties.setColumnCount(2)
        self.tblFileProperties.setHorizontalHeaderLabels(["Property", "Value"])
        properties_header = self.tblFileProperties.horizontalHeader()
        properties_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tblFileProperties.setColumnWidth(0, 150)
        properties_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # table headers of tblFileHistory are Timestamp and Event
        self.tblFileHistory.setColumnCount(2)
        self.tblFileHistory.setHorizontalHeaderLabels(["Timestamp", "Event"])
        history_header = self.tblFileHistory.horizontalHeader()
        history_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tblFileHistory.setColumnWidth(0, 150)
        history_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def __populate(self):
        """Populate the dialog with data."""
        properties = self.controller.get_properties()
        history_entries = self.controller.get_history_entries()
        self.__populate_properties(properties)
        self.__populate_history(history_entries)

    def __populate_properties(self, properties: dict):
        """Populate the properties table."""
        self.tblFileProperties.setRowCount(len(properties))
        for i, (key, value) in enumerate(properties.items()):
            self.tblFileProperties.setItem(i, 0, QTableWidgetItem(key))
            self.tblFileProperties.setItem(i, 1, QTableWidgetItem(value))

    def __populate_history(self, history_entries: dict):
        """Populate the history table."""
        self.tblFileHistory.setRowCount(len(history_entries))
        for i, (key, value) in enumerate(history_entries.items()):
            self.tblFileHistory.setItem(i, 0, QTableWidgetItem(human_timestamp_from(key)))
            self.tblFileHistory.setItem(i, 1, QTableWidgetItem(value))
