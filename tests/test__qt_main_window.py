import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import (
    QApplication,
    QTableWidget,
    QPushButton,
)
from aoget.view.main_window import MainWindow


class TestMainWindow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def setUp(self):
        aoget_db = MagicMock()
        self.controller_mock = MagicMock()
        self.window = MainWindow(aoget_db, controller=self.controller_mock, show=False)
        self.window.tblJobs = QTableWidget()
        self.window.btnJobStart = QPushButton()
        self.window.btnJobStop = QPushButton()
        self.window.btnJobThreadsPlus = QPushButton()
        self.window.btnJobThreadsMinus = QPushButton()
        self.window.btnJobCreate = QPushButton()
        self.window.btnJobEdit = QPushButton()
        self.window.btnJobRemoveFromList = QPushButton()
        self.window.btnJobRemove = QPushButton()
        self.window.btnJobExport = QPushButton()
        self.window.btnJobImport = QPushButton()
        self.window.btnJobOpenLink = QPushButton()
        self.window.btnJobHealthCheck = QPushButton()
        self.window.tblFiles = QTableWidget()
        self.window.tblFiles.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.window.tblFiles.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.window.btnFileStartDownload = QPushButton()
        self.window.btnFileStopDownload = QPushButton()
        self.window.btnFileRedownload = QPushButton()
        self.window.btnFileRemoveFromList = QPushButton()
        self.window.btnFileRemove = QPushButton()
        self.window.btnFileDetails = QPushButton()
        self.window.btnFileShowInFolder = QPushButton()
        self.window.btnFileCopyURL = QPushButton()
        self.window.btnFileOpenLink = QPushButton()
        self.window.btnFilePriorityPlus = QPushButton()
        self.window.btnFilePriorityMinus = QPushButton()

    def test_setup_ui(self):
        self.window._MainWindow__setup_ui()

    @patch("aoget.view.main_window.confirmation_dialog", return_value=True)
    def tearDown(self, mock_confirmation_dialog):
        self.window.close()


if __name__ == '__main__':
    unittest.main()
