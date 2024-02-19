import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import (
    QApplication,
    QTableWidgetItem,
    QMainWindow,
    QTableWidget,
    QPushButton,
)
from aoget.view.main_window_files import (
    MainWindowFiles,
    FILE_NAME_IDX,
    FILE_STATUS_IDX,
    FILE_SIZE_IDX,
    FILE_PROGRESS_IDX,
)
from aoget.model.dto.file_model_dto import FileModelDTO


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

    def test_show_files(self):
        self.window.tblFiles.setRowCount(2)
        self.window.tblFiles.setColumnCount(1)
        self.window.tblFiles.setItem(0, 0, QTableWidgetItem("Test File"))
        self.window.tblFiles.setItem(1, 0, QTableWidgetItem("Test File 2"))
        self.assertEqual(self.window.tblFiles.rowCount(), 2)
        self.main_window_files.show_files(None)
        # Assert that rows go hidden if no job is selected
        for i in range(self.window.tblFiles.rowCount()):
            self.assertTrue(self.window.tblFiles.isRowHidden(i))

    def test_set_file_at_row(self):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        self.window.tblFiles.setRowCount(1)
        self.main_window_files.set_file_at_row(0, file_dto)
        # Assert that the file has been set at the given row
        self.assertEqual(
            self.window.tblFiles.item(0, FILE_NAME_IDX).text(), "test_file.txt"
        )
        self.assertEqual(
            self.window.tblFiles.item(0, FILE_STATUS_IDX).text(), "Downloading"
        )
        self.assertEqual(self.window.tblFiles.item(0, FILE_SIZE_IDX).text(), "10.0MB")
        self.assertEqual(
            self.window.tblFiles.cellWidget(0, FILE_PROGRESS_IDX).value(), 10
        )

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

    def test_update_file(self):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        self.window.tblFiles.setRowCount(1)
        self.main_window_files.set_file_at_row(0, file_dto)
        # Assert that the file has been set at the given row
        self.assertEqual(
            self.window.tblFiles.item(0, FILE_NAME_IDX).text(), "test_file.txt"
        )
        self.assertEqual(
            self.window.tblFiles.item(0, FILE_STATUS_IDX).text(), "Downloading"
        )
        self.assertEqual(self.window.tblFiles.item(0, FILE_SIZE_IDX).text(), "10.0MB")
        self.assertEqual(
            self.window.tblFiles.cellWidget(0, FILE_PROGRESS_IDX).value(), 10
        )
        updated_file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        updated_file_dto.job_name = "Test Job"
        updated_file_dto.downloaded_bytes = 1024 * 1024 * 2
        updated_file_dto.size_bytes = 1024 * 1024 * 10
        updated_file_dto.percent_completed = 20
        updated_file_dto.status = "Downloading"
        self.window.tblFiles.selectRow(0)
        self.main_window_files.update_file(updated_file_dto)
        self.assertEqual(
            self.window.tblFiles.item(0, FILE_NAME_IDX).text(), "test_file.txt"
        )
        self.assertEqual(
            self.window.tblFiles.item(0, FILE_STATUS_IDX).text(), "Downloading"
        )
        self.assertEqual(self.window.tblFiles.item(0, FILE_SIZE_IDX).text(), "10.0MB")
        self.assertEqual(
            self.window.tblFiles.cellWidget(0, FILE_PROGRESS_IDX).value(), 20
        )
        self.assertFalse(self.window.btnFileStartDownload.isEnabled())

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

    @patch("aoget.view.main_window_files.FileDetailsDialog")
    def test_on_file_details(self, file_details_dialog_mock):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        self.window.tblFiles.setRowCount(1)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.window.tblFiles.selectRow(0)
        self.main_window_files._MainWindowFiles__on_file_details()
        file_details_dialog_mock.assert_called_once()

    def tearDown(self):
        self.window = None

    def test_single_file_download(self):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        self.window.tblFiles.setRowCount(1)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.window.tblFiles.selectRow(0)
        self.controller_mock.start_download.return_value = (True, None)
        self.main_window_files._MainWindowFiles__on_file_start_download()
        self.controller_mock.start_download.assert_called_with(
            "Test Job", "test_file.txt"
        )

    def test_multi_file_download(self):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        file_dto_2 = FileModelDTO.from_url("http://test.com/test_file_2.txt")
        file_dto_2.job_name = "Test Job"
        file_dto_2.downloaded_bytes = 1024 * 1024
        file_dto_2.size_bytes = 1024 * 1024 * 10
        file_dto_2.percent_completed = 10
        file_dto_2.status = "Downloading"
        self.window.tblFiles.setRowCount(2)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.main_window_files.set_file_at_row(1, file_dto_2)
        # Qt inconsistent API for ExtendedSelection: multiple selects are not supported
        # programmatically, despite supported by the UI
        self.window.tblFiles.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.window.tblFiles.selectRow(0)
        self.window.tblFiles.selectRow(1)
        self.main_window_files._MainWindowFiles__on_file_start_download()
        self.controller_mock.start_downloads.assert_called_with(
            "Test Job", ["test_file.txt", "test_file_2.txt"]
        )

    def test_single_file_stop(self):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        self.window.tblFiles.setRowCount(1)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.window.tblFiles.selectRow(0)
        self.controller_mock.stop_download.return_value = (True, None)
        self.main_window_files._MainWindowFiles__on_file_stop_download()
        self.controller_mock.stop_download.assert_called_with(
            "Test Job", "test_file.txt"
        )

    def test_multi_file_stop(self):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        file_dto_2 = FileModelDTO.from_url("http://test.com/test_file_2.txt")
        file_dto_2.job_name = "Test Job"
        file_dto_2.downloaded_bytes = 1024 * 1024
        file_dto_2.size_bytes = 1024 * 1024 * 10
        file_dto_2.percent_completed = 10
        file_dto_2.status = "Downloading"
        self.window.tblFiles.setRowCount(2)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.main_window_files.set_file_at_row(1, file_dto_2)
        # Qt inconsistent API for ExtendedSelection: multiple selects are not supported
        # programmatically, despite supported by the UI
        self.window.tblFiles.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.window.tblFiles.selectRow(0)
        self.window.tblFiles.selectRow(1)
        self.main_window_files._MainWindowFiles__on_file_stop_download()
        self.controller_mock.stop_downloads.assert_called_with(
            "Test Job", ["test_file.txt", "test_file_2.txt"]
        )

    @patch("aoget.view.main_window_files.confirmation_dialog", return_value=True)
    def test_single_file_remove_from_list(self, confirmation_dialog_mock):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        self.window.tblFiles.setRowCount(1)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.window.tblFiles.selectRow(0)
        self.controller_mock.remove_file_from_job.return_value = (True, None)
        self.main_window_files._MainWindowFiles__on_file_remove_from_list()
        self.controller_mock.remove_file_from_job.assert_called_with(
            "Test Job", "test_file.txt", delete_from_disk=False
        )
        # since response was okay, files should be hidden at this stage
        self.assertTrue(self.window.tblFiles.isRowHidden(0))
        self.assertFalse(self.window.tblFiles.isRowHidden(1))

    @patch("aoget.view.main_window_files.confirmation_dialog", return_value=True)
    @patch("aoget.view.main_window_files.show_warnings")
    def test_multi_file_remove_from_list(
        self, confirmation_dialog_mock, show_warnings_mock
    ):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        file_dto_2 = FileModelDTO.from_url("http://test.com/test_file_2.txt")
        file_dto_2.job_name = "Test Job"
        file_dto_2.downloaded_bytes = 1024 * 1024
        file_dto_2.size_bytes = 1024 * 1024 * 10
        file_dto_2.percent_completed = 10
        file_dto_2.status = "Downloading"
        self.window.tblFiles.setRowCount(2)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.main_window_files.set_file_at_row(1, file_dto_2)
        # Qt inconsistent API for ExtendedSelection: multiple selects are not supported
        # programmatically, despite supported by the UI
        self.window.tblFiles.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.window.tblFiles.selectRow(0)
        self.window.tblFiles.selectRow(1)
        self.main_window_files._MainWindowFiles__on_file_remove_from_list()
        self.controller_mock.remove_files_from_job.assert_called_with(
            "Test Job", ["test_file.txt", "test_file_2.txt"]
        )

    @patch("aoget.view.main_window_files.confirmation_dialog", return_value=True)
    def test_single_file_remove_from_disk(self, confirmation_dialog_mock):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        self.window.tblFiles.setRowCount(1)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.window.tblFiles.selectRow(0)
        self.controller_mock.remove_file_from_job.return_value = (True, None)
        self.main_window_files._MainWindowFiles__on_file_remove()
        self.controller_mock.remove_file_from_job.assert_called_with(
            "Test Job", "test_file.txt", delete_from_disk=True
        )
        # since response was okay, files should be hidden at this stage
        self.assertTrue(self.window.tblFiles.isRowHidden(0))
        self.assertFalse(self.window.tblFiles.isRowHidden(1))

    @patch("aoget.view.main_window_files.confirmation_dialog", return_value=True)
    @patch("aoget.view.main_window_files.show_warnings")
    def test_multi_file_remove_from_disk(
        self, confirmation_dialog_mock, show_warnings_mock
    ):
        self.main_window_files.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, QTableWidgetItem("Test Job"))
        self.window.tblJobs.selectRow(0)
        file_dto = FileModelDTO.from_url("http://test.com/test_file.txt")
        file_dto.job_name = "Test Job"
        file_dto.downloaded_bytes = 1024 * 1024
        file_dto.size_bytes = 1024 * 1024 * 10
        file_dto.percent_completed = 10
        file_dto.status = "Downloading"
        file_dto_2 = FileModelDTO.from_url("http://test.com/test_file_2.txt")
        file_dto_2.job_name = "Test Job"
        file_dto_2.downloaded_bytes = 1024 * 1024
        file_dto_2.size_bytes = 1024 * 1024 * 10
        file_dto_2.percent_completed = 10
        file_dto_2.status = "Downloading"
        self.window.tblFiles.setRowCount(2)
        self.main_window_files.set_file_at_row(0, file_dto)
        self.main_window_files.set_file_at_row(1, file_dto_2)
        # Qt inconsistent API for ExtendedSelection: multiple selects are not supported
        # programmatically, despite supported by the UI
        self.window.tblFiles.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)
        self.window.tblFiles.selectRow(0)
        self.window.tblFiles.selectRow(1)
        self.main_window_files._MainWindowFiles__on_file_remove()
        self.controller_mock.remove_files_from_job.assert_called_with(
            "Test Job", ["test_file.txt", "test_file_2.txt"], delete_from_disk=True
        )


if __name__ == '__main__':
    unittest.main()
