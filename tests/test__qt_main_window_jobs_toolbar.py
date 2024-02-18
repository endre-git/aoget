import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidget,
    QPushButton,
    QTableWidgetItem,
)
from PyQt6.QtCore import QUrl
from aoget.view.main_window_jobs import MainWindowJobs
from aoget.model.dto.job_dto import JobDTO
from aoget.view.main_window_jobs import (
    JOB_NAME_IDX,
    JOB_STATUS_IDX,
)


class MockMainWindow(QMainWindow):
    def show_files(self, job_name):
        pass


class TestMainWindowJobs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def setUp(self):
        self.window = MockMainWindow()
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
        self.assertTrue(self.window.btnJobImport.isEnabled())
        self.assertFalse(self.window.btnJobOpenLink.isEnabled())
        self.assertFalse(self.window.btnJobHealthCheck.isEnabled())

    def test_update_job_toolbar_resuming_job(self):
        job = JobDTO(
            id=-1,
            name="Test Job",
            status="Resuming",
            threads_active=1,
            threads_allocated=3,
            total_size_bytes=123123123,
            downloaded_bytes=123123123,
            selected_files_count=10,
            selected_files_with_known_size=10,
            files_done=10,
            page_url="http://test.com",
        )
        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.main_window_jobs.resuming_jobs.append("Test Job")
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.selectRow(0)
        self.main_window_jobs.set_job_at_row(0, job)
        item = self.window.tblJobs.item(0, JOB_NAME_IDX)
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "Test Job")
        QApplication.processEvents()
        self.main_window_jobs.update_job_toolbar()
        self.assertFalse(self.window.btnJobStart.isEnabled())
        self.assertFalse(self.window.btnJobStop.isEnabled())
        self.assertFalse(self.window.btnJobThreadsPlus.isEnabled())
        self.assertFalse(self.window.btnJobThreadsMinus.isEnabled())
        self.assertFalse(self.window.btnJobEdit.isEnabled())
        self.assertFalse(self.window.btnJobRemoveFromList.isEnabled())
        self.assertFalse(self.window.btnJobRemove.isEnabled())
        self.assertFalse(self.window.btnJobExport.isEnabled())
        self.assertTrue(self.window.btnJobImport.isEnabled())
        self.assertFalse(self.window.btnJobOpenLink.isEnabled())
        self.assertFalse(self.window.btnJobHealthCheck.isEnabled())

    def test_update_job_toolbar_running_job(self):
        job = JobDTO(
            id=-1,
            name="Test Job",
            status="Running",
            threads_active=1,
            threads_allocated=3,
            total_size_bytes=123123123,
            downloaded_bytes=123123123,
            selected_files_count=10,
            selected_files_with_known_size=10,
            files_done=10,
            page_url="http://test.com",
        )
        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.selectRow(0)
        self.main_window_jobs.set_job_at_row(0, job)
        item = self.window.tblJobs.item(0, JOB_NAME_IDX)
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "Test Job")
        QApplication.processEvents()
        self.main_window_jobs.update_job_toolbar()
        self.assertTrue(self.window.btnJobStart.isEnabled())
        self.assertTrue(self.window.btnJobStop.isEnabled())
        self.assertTrue(self.window.btnJobThreadsPlus.isEnabled())
        self.assertTrue(self.window.btnJobThreadsMinus.isEnabled())
        self.assertTrue(self.window.btnJobEdit.isEnabled())
        self.assertTrue(self.window.btnJobRemoveFromList.isEnabled())
        self.assertTrue(self.window.btnJobRemove.isEnabled())
        self.assertTrue(self.window.btnJobExport.isEnabled())
        self.assertTrue(self.window.btnJobImport.isEnabled())
        self.assertTrue(self.window.btnJobOpenLink.isEnabled())
        self.assertTrue(self.window.btnJobHealthCheck.isEnabled())

    @patch("aoget.view.main_window_jobs.show_warnings")
    @patch("aoget.view.main_window_jobs.confirmation_dialog", return_value=True)
    def test_job_remove_from_list(self, mock_show_warnings, mock_confirmation_dialog):
        job = JobDTO(
            id=-1,
            name="Test Job",
            status="Running",
            threads_active=1,
            threads_allocated=3,
            total_size_bytes=123123123,
            downloaded_bytes=123123123,
            selected_files_count=10,
            selected_files_with_known_size=10,
            files_done=10,
            page_url="http://test.com",
        )
        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.selectRow(0)
        self.main_window_jobs.set_job_at_row(0, job)
        item = self.window.tblJobs.item(0, JOB_NAME_IDX)
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "Test Job")
        QApplication.processEvents()
        self.window.btnJobRemoveFromList.click()
        self.controller_mock.delete_job.assert_called_once_with("Test Job")

    @patch("aoget.view.main_window_jobs.show_warnings")
    @patch("aoget.view.main_window_jobs.confirmation_dialog", return_value=True)
    def test_job_remove(self, mock_show_warnings, mock_confirmation_dialog):
        job = JobDTO(
            id=-1,
            name="Test Job",
            status="Running",
            threads_active=1,
            threads_allocated=3,
            total_size_bytes=123123123,
            downloaded_bytes=123123123,
            selected_files_count=10,
            selected_files_with_known_size=10,
            files_done=10,
            page_url="http://test.com",
        )
        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.selectRow(0)
        self.main_window_jobs.set_job_at_row(0, job)
        item = self.window.tblJobs.item(0, JOB_NAME_IDX)
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "Test Job")
        QApplication.processEvents()
        self.window.btnJobRemove.click()
        self.controller_mock.delete_job.assert_called_once_with(
            "Test Job", delete_from_disk=True
        )

    @patch("aoget.view.main_window_jobs.error_dialog")
    def test_job_export_size_not_resolved(self, mock_error_dialog):
        job = JobDTO(
            id=-1,
            name="Test Job",
            status="Not Running",
            threads_active=1,
            threads_allocated=3,
            total_size_bytes=123123123,
            downloaded_bytes=123123123,
            selected_files_count=10,
            selected_files_with_known_size=8,
            files_done=10,
            page_url="http://test.com",
        )
        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.selectRow(0)
        self.main_window_jobs.set_job_at_row(0, job)
        item = self.window.tblJobs.item(0, JOB_NAME_IDX)
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "Test Job")
        QApplication.processEvents()
        self.controller_mock.get_job_dto_by_name.return_value = job
        self.window.btnJobExport.click()
        mock_error_dialog.assert_called_once()

    @patch(
        "aoget.view.main_window_jobs.QFileDialog.getSaveFileName",
        return_value=("test_file", "csv"),
    )
    def test_job_export(self, mock_get_open_file_name):
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

        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.selectRow(0)
        self.main_window_jobs.set_job_at_row(0, job)
        item = self.window.tblJobs.item(0, JOB_NAME_IDX)
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "Test Job")
        QApplication.processEvents()
        self.controller_mock.get_job_dto_by_name.return_value = job
        self.window.btnJobExport.click()
        self.controller_mock.export_job.assert_called_once_with("Test Job", "test_file")

    @patch(
        "aoget.view.main_window_jobs.QFileDialog.getOpenFileName",
        return_value=("test_file", "csv"),
    )
    @patch("aoget.view.main_window_jobs.JobEditorDialog", return_value=MagicMock())
    def test_job_import(self, mock_get_open_file_name, mock_job_editor_dialog):
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
        file_dtos = [
            MagicMock(),
            MagicMock(),
        ]

        mock_job_editor_dialog.exec.return_value = 1

        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.controller_mock.get_job_dto_by_name.return_value = job
        self.controller_mock.import_job.return_value = (job, file_dtos)
        self.window.btnJobImport.click()
        self.controller_mock.import_job.assert_called_once_with("test_file")

    @patch("aoget.view.main_window_jobs.QDesktopServices.openUrl")
    def test_open_link(self, mock_open_url):
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

        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.window.tblJobs.setRowCount(1)
        self.window.tblJobs.selectRow(0)
        self.main_window_jobs.set_job_at_row(0, job)
        item = self.window.tblJobs.item(0, JOB_NAME_IDX)
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "Test Job")
        QApplication.processEvents()
        self.controller_mock.get_job_dto_by_name.return_value = job
        self.window.btnJobOpenLink.click()
        mock_open_url.assert_called_once_with(QUrl("http://test.com"))

    @patch(
        "aoget.view.main_window_jobs.QFileDialog.getOpenFileName",
        return_value=("test_file", "csv"),
    )
    @patch("aoget.view.main_window_jobs.JobEditorDialog", return_value=MagicMock())
    def test_create_job(self, mock_get_open_file_name, mock_job_editor_dialog):
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
        file_dtos = [
            MagicMock(),
            MagicMock(),
        ]

        mock_job_editor_dialog.exec.return_value = 1

        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.controller_mock.get_job_dto_by_name.return_value = job
        self.controller_mock.import_job.return_value = (job, file_dtos)
        self.window.btnJobCreate.click()

    @patch(
        "aoget.view.main_window_jobs.QFileDialog.getOpenFileName",
        return_value=("test_file", "csv"),
    )
    @patch("aoget.view.main_window_jobs.JobEditorDialog", return_value=MagicMock())
    def test_edit_job(self, mock_get_open_file_name, mock_job_editor_dialog):
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
        file_dtos = [
            MagicMock(),
            MagicMock(),
        ]

        mock_job_editor_dialog.exec.return_value = 1

        self.window.tblJobs.clear()
        self.main_window_jobs.setup_ui()
        self.controller_mock.get_job_dto_by_name.return_value = job
        self.controller_mock.import_job.return_value = (job, file_dtos)
        self.window.btnJobEdit.click()

    def tearDown(self):
        self.window.close()


if __name__ == '__main__':
    unittest.main()
