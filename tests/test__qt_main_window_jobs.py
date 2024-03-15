import unittest
from unittest.mock import MagicMock, patch, call
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidget,
    QPushButton,
    QTableWidgetItem,
)
from aoget.view.main_window_jobs import MainWindowJobs
from aoget.model.dto.job_dto import JobDTO


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

    def test_setup_ui(self):
        self.main_window_jobs.setup_ui()
        # Assert that table has been set up
        self.assertEqual(self.window.tblJobs.columnCount(), 9)
        self.assertEqual(self.window.tblJobs.rowCount(), 0)  # Initially no rows

    @patch("aoget.view.main_window_jobs.MainWindowJobs.set_job_at_row")
    def test_update_table_empty_list(self, mock_set_job_at_row):
        self.controller_mock.jobs.get_job_dtos.return_value = []
        self.main_window_jobs.update_table()
        self.assertEqual(self.window.tblJobs.rowCount(), 0)
        self.assertFalse(mock_set_job_at_row.called)

    def test_update_table_one_job(self):
        self.main_window_jobs.setup_ui()
        job = JobDTO(id=-1, name="Test Job", status="Running")
        self.controller_mock.jobs.get_job_dtos.return_value = [job]
        self.main_window_jobs.update_table()
        self.assertEqual(self.window.tblJobs.rowCount(), 1)
        self.assertEqual(self.window.tblJobs.item(0, 0).text(), "Test Job")

    def test_update_job(self):
        self.main_window_jobs.setup_ui()
        job = JobDTO(id=-1, name="Test Job", status="Running")
        self.controller_mock.jobs.get_job_dtos.return_value = [job]
        self.main_window_jobs.update_table()
        updated_job = JobDTO(id=-1, name="Test Job", status="Not running")
        self.main_window_jobs.update_job(updated_job)
        self.assertEqual(self.window.tblJobs.rowCount(), 1)

    def test_get_row_index_of_job(self):
        self.main_window_jobs.setup_ui()
        job = JobDTO(id=-1, name="Test Job", status="Running")
        self.controller_mock.jobs.get_job_dtos.return_value = [job]
        self.main_window_jobs.update_table()
        row_index = self.main_window_jobs._MainWindowJobs__get_row_index_of_job("Test Job")
        self.assertEqual(row_index, 0)

    @patch("aoget.view.main_window_jobs.MainWindowJobs.set_job_at_row")
    def test_update_table_multiple_jobs(self, mock_set_job_at_row):
        jobs = [
            JobDTO(id=1, name="Job1", status="Running"),
            JobDTO(id=2, name="Job2", status="Paused"),
            JobDTO(id=3, name="Job3", status="Completed"),
        ]
        self.controller_mock.jobs.get_job_dtos.return_value = jobs
        self.main_window_jobs.update_table()
        self.assertEqual(self.window.tblJobs.rowCount(), 3)
        calls = [call(i, job) for i, job in enumerate(jobs)]
        mock_set_job_at_row.assert_has_calls(calls)

    def test_is_job_selected_no_selection(self):
        self.assertFalse(self.main_window_jobs.is_job_selected())

    def test_is_job_selected_one_item_selected(self):
        item = QTableWidgetItem("Test Job")
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.setColumnCount(1)
        self.window.tblJobs.setItem(0, 0, item)
        self.window.tblJobs.setCurrentItem(item)
        self.assertTrue(self.main_window_jobs.is_job_selected())

    def tearDown(self):
        self.window.close()


if __name__ == '__main__':
    unittest.main()
