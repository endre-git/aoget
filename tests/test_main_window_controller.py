import unittest
from unittest.mock import MagicMock, patch
from aoget.model.job import Job
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.controller.main_window_controller import MainWindowController


class TestMainWindowController(unittest.TestCase):
    def setUp(self):
        self.main_window = MagicMock()
        self.aoget_db = MagicMock()
        self.controller = MainWindowController(self.main_window, self.aoget_db)

    def test_set_global_bandwidth_limit(self):
        self.controller.set_global_bandwidth_limit(100000)
        self.assertEqual(self.controller.handlers.rate_limiter.rate_limit_bps, 100000)

    def test_actualize_config(self):
        job_downloader = MagicMock()
        self.controller.handlers.downloads.job_downloaders = {
            "test_job": job_downloader
        }
        with patch(
            "aoget.controller.main_window_controller.get_config_value"
        ) as mock_get_config_value:
            mock_get_config_value.return_value = 10
            self.controller.actualize_config()
            self.assertEqual(job_downloader.download_retry_attempts, 10)

    @patch("aoget.controller.main_window_controller.get_crash_report")
    @patch("aoget.controller.main_window_controller.get_job_dao")
    @patch("aoget.controller.main_window_controller.get_file_model_dao")
    def test_resume_state(
        self, mock_get_file_model_dao, mock_get_job_dao, mock_get_crash_report
    ):
        mock_get_crash_report.return_value = None
        test_job = Job(
            id=100,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
            threads_allocated=2,
        )
        file_dto_1 = FileModelDTO(
            job_name='test_job',
            url='http://example.com/file_name',
            name='file_name',
            status='Stopped',
            selected=True,
            size_bytes=100,
        )
        file_dto_2 = FileModelDTO(
            job_name='test_job',
            url='http://example.com/file_name2',
            name='file_name2',
            status='Stopped',
            selected=True,
            size_bytes=100,
        )
        file_dto_3 = FileModelDTO(
            job_name='test_job',
            url='http://example.com/file_name3',
            name='file_name3',
            status='Stopped',
            selected=True,
        )
        mock_get_job_dao.return_value.get_all_jobs.return_value = [test_job]
        mock_get_file_model_dao.return_value.get_total_downloaded_bytes_for_job.return_value = (
            300
        )
        self.controller.files = MagicMock()
        files = {
            "file_name": file_dto_1,
            "file_name2": file_dto_2,
            "file_name3": file_dto_3,
        }
        self.controller.files.get_selected_file_dtos.return_value = files
        self.controller.jobs = MagicMock()
        self.controller.cache = MagicMock()
        self.controller.resume_state()
        self.controller.jobs.start_size_resolver_for_job.assert_called_once_with(
            "test_job"
        )
        self.assertEqual(300, test_job.downloaded_bytes)
        self.controller.cache.set_cache.assert_called_with({"test_job": files})


if __name__ == "__main__":
    unittest.main()
