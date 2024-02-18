import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidget,
    QPushButton,
    QTableWidgetItem,
)
from aoget.view.main_window_jobs import MainWindowJobs
from aoget.model.dto.job_dto import JobDTO
from aoget.view.main_window_jobs import (
    JOB_NAME_IDX,
    JOB_STATUS_IDX,
    JOB_THREADS_IDX,
    JOB_SIZE_IDX,
    JOB_FILES_IDX,
    JOB_PROGRESS_IDX,
)


class TestMainWindowJobs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def setUp(self):
        self.window = QMainWindow()
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
        self.controller_mock = MagicMock()
        self.main_window_jobs = MainWindowJobs(self.window)
        self.window.controller = self.controller_mock

    def test_job_start_stop_threads_nothing_selected(self):
        self.main_window_jobs._MainWindowJobs__on_job_start()
        self.assertFalse(self.controller_mock.start_job.called)
        self.main_window_jobs._MainWindowJobs__on_job_stop()
        self.assertFalse(self.controller_mock.stop_job.called)
        self.main_window_jobs._MainWindowJobs__on_job_threads_plus()
        self.assertFalse(self.controller_mock.add_thread.called)
        self.main_window_jobs._MainWindowJobs__on_job_threads_minus()
        self.assertFalse(self.controller_mock.remove_thread.called)

    def test_job_start_stop_threads_one_selected(self):
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        item = QTableWidgetItem("Test Job")
        self.window.tblJobs.setItem(0, 0, item)
        self.window.tblJobs.setCurrentItem(item)
        self.main_window_jobs._MainWindowJobs__on_job_start()
        self.controller_mock.start_job.assert_called_once_with("Test Job")
        self.main_window_jobs._MainWindowJobs__on_job_stop()
        self.controller_mock.stop_job.assert_called_once_with("Test Job")
        self.main_window_jobs._MainWindowJobs__on_job_threads_plus()
        self.controller_mock.add_thread.assert_called_once_with("Test Job")
        self.main_window_jobs._MainWindowJobs__on_job_threads_minus()
        self.controller_mock.remove_thread.assert_called_once_with("Test Job")

    def test_set_job_at_row_job_completed(self):
        job = JobDTO(
            id=-1,
            name="Test Job",
            status="Not Running",
            threads_active=1,
            threads_allocated=3,
            total_size_bytes=123123123,
            downloaded_bytes=123123123,
            selected_files_count=10,
            selected_files_with_known_size=10,
            files_done=10,
            page_url="http://test.com",
        )

        self.main_window_jobs.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.main_window_jobs.set_job_at_row(0, job)
        self.assertEqual(self.window.tblJobs.item(0, JOB_NAME_IDX).text(), "Test Job")
        self.assertEqual(
            self.window.tblJobs.item(0, JOB_STATUS_IDX).text(), "Not Running"
        )

    def test_update_job_toolbar_no_selection(self):
        self.main_window_jobs.update_job_toolbar()
        self.assertFalse(self.window.btnJobStart.isEnabled())
        self.assertFalse(self.window.btnJobStop.isEnabled())
        self.assertFalse(self.window.btnJobThreadsPlus.isEnabled())
        self.assertFalse(self.window.btnJobThreadsMinus.isEnabled())
        self.assertFalse(self.window.btnJobEdit.isEnabled())
        self.assertFalse(self.window.btnJobRemoveFromList.isEnabled())
        self.assertFalse(self.window.btnJobRemove.isEnabled())
        self.assertFalse(self.window.btnJobExport.isEnabled())
        self.assertFalse(self.window.btnJobImport.isEnabled())
        self.assertFalse(self.window.btnJobOpenLink.isEnabled())
        self.assertFalse(self.window.btnJobHealthCheck.isEnabled())

    def tearDown(self):
        self.window.close()


if __name__ == '__main__':
    unittest.main()
