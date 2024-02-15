import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidget, QPushButton, QTableWidgetItem
from aoget.view.main_window_jobs import MainWindowJobs


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

    def tearDown(self):
        self.window.close()


if __name__ == '__main__':
    unittest.main()
