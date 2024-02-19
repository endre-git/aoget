import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import (
    QApplication,
    QTableWidgetItem,
    QMainWindow,
    QTableWidget,
    QPushButton,
)
from aoget.view.main_window_files import MainWindowFiles


class MockMainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.job_selected = True

    def is_job_selected(self):
        return self.job_selected

    def get_selected_job_name(self):
        return "Test Job" if self.job_selected else None


class TestMainWindowFiles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def setUp(self):
        self.window = MockMainWindow()
        self.window.tblJobs = QTableWidget()
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
        self.controller_mock = MagicMock()
        self.main_window_files = MainWindowFiles(self.window)
        self.window.controller = self.controller_mock
        self.window.jobs_table_view = MagicMock()
        self.window.files_table_view = self.main_window_files

    def add_job(self):
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))

    def test_setup_ui(self):
        self.main_window_files.setup_ui()
        # Assert that table has been set up
        self.assertEqual(self.window.tblFiles.columnCount(), 9)
        self.assertEqual(self.window.tblFiles.rowCount(), 0)  # Initially no rows

    def test_nothing_selected(self):
        self.window.job_selected = False
        self.assertTrue(self.main_window_files.nothing_selected())

    def test_show_files_no_job_selected(self):
        self.window.tblFiles.setRowCount(2)
        self.window.tblFiles.setColumnCount(1)
        self.window.tblFiles.setItem(0, 0, QTableWidgetItem("Test File"))
        self.window.tblFiles.setItem(1, 0, QTableWidgetItem("Test File 2"))
        self.assertEqual(self.window.tblFiles.rowCount(), 2)
        self.main_window_files.show_files(None)
        # Assert that rows go hidden if no job is selected
        for i in range(self.window.tblFiles.rowCount()):
            self.assertTrue(self.window.tblFiles.isRowHidden(i))

    def test_update_file_toolbar_no_file_selected(self):
        self.window.jobs_table_view.resuming_jobs = []
        self.main_window_files.update_file_toolbar()
        # Assert that all file toolbar buttons are disabled
        self.assertFalse(self.window.btnFileStartDownload.isEnabled())
        self.assertFalse(self.window.btnFileStopDownload.isEnabled())
        self.assertFalse(self.window.btnFileRedownload.isEnabled())
        self.assertFalse(self.window.btnFileRemoveFromList.isEnabled())
        self.assertFalse(self.window.btnFileRemove.isEnabled())
        self.assertFalse(self.window.btnFileDetails.isEnabled())
        self.assertFalse(self.window.btnFileShowInFolder.isEnabled())
        self.assertFalse(self.window.btnFileCopyURL.isEnabled())
        self.assertFalse(self.window.btnFileOpenLink.isEnabled())
        self.assertFalse(self.window.btnFilePriorityPlus.isEnabled())
        self.assertFalse(self.window.btnFilePriorityMinus.isEnabled())

    def test_update_file_toolbar_single_file_selected(self):
        self.window.tblFiles.setRowCount(2)
        self.window.tblFiles.setColumnCount(4)
        self.window.tblFiles.setItem(0, 0, QTableWidgetItem("Test File"))
        self.window.tblFiles.setItem(0, 3, QTableWidgetItem("Downloading"))
        self.window.tblFiles.setItem(1, 0, QTableWidgetItem("Test File 2"))
        self.window.tblFiles.setItem(1, 3, QTableWidgetItem("Stopped"))
        self.assertEqual(self.window.tblFiles.rowCount(), 2)
        self.window.tblFiles.selectRow(0)

        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)

        self.main_window_files.update_file_toolbar()
        # Assert that all file toolbar buttons are disabled

        # Assert that specific file toolbar buttons are enabled
        self.assertTrue(self.window.btnFileRedownload.isEnabled())
        self.assertTrue(self.window.btnFileRemoveFromList.isEnabled())
        self.assertTrue(self.window.btnFileRemove.isEnabled())
        self.assertTrue(self.window.btnFileDetails.isEnabled())
        self.assertTrue(self.window.btnFileShowInFolder.isEnabled())
        self.assertTrue(self.window.btnFileCopyURL.isEnabled())
        self.assertTrue(self.window.btnFileOpenLink.isEnabled())
        self.assertTrue(self.window.btnFilePriorityPlus.isEnabled())
        self.assertTrue(self.window.btnFilePriorityMinus.isEnabled())
        # Assert that start/stop buttons are updated based on file status
        self.assertFalse(self.window.btnFileStartDownload.isEnabled())
        self.assertTrue(self.window.btnFileStopDownload.isEnabled())

    def test_update_file_toolbar_multiple_files_selected(self):
        self.window.tblFiles.setRowCount(2)
        self.window.tblFiles.setColumnCount(4)
        self.window.tblFiles.setItem(0, 0, QTableWidgetItem("Test File"))
        self.window.tblFiles.setItem(0, 3, QTableWidgetItem("Downloading"))
        self.window.tblFiles.setItem(1, 0, QTableWidgetItem("Test File 2"))
        self.window.tblFiles.setItem(1, 3, QTableWidgetItem("Stopped"))
        self.assertEqual(self.window.tblFiles.rowCount(), 2)
        self.window.tblFiles.selectRow(0)
        self.window.tblFiles.selectRow(1)

        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)

        self.main_window_files.update_file_toolbar()
        # Assert that all file toolbar buttons are disabled

        # Assert that specific file toolbar buttons are enabled
        self.assertFalse(self.window.btnFileRedownload.isEnabled())
        self.assertTrue(self.window.btnFileRemoveFromList.isEnabled())
        self.assertTrue(self.window.btnFileRemove.isEnabled())
        self.assertFalse(self.window.btnFileDetails.isEnabled())
        self.assertFalse(self.window.btnFileShowInFolder.isEnabled())
        self.assertFalse(self.window.btnFileCopyURL.isEnabled())
        self.assertFalse(self.window.btnFileOpenLink.isEnabled())
        self.assertTrue(self.window.btnFilePriorityPlus.isEnabled())
        self.assertTrue(self.window.btnFilePriorityMinus.isEnabled())
        # Assert that start/stop buttons are updated based on file status
        self.assertTrue(self.window.btnFileStartDownload.isEnabled())
        self.assertTrue(self.window.btnFileStopDownload.isEnabled())

    def tearDown(self):
        self.window = None


if __name__ == '__main__':
    unittest.main()
