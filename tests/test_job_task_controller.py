import unittest
from unittest.mock import MagicMock, patch
from aoget.controller.job_task_controller import JobTaskController


class TestJobTaskController(unittest.TestCase):

    def setUp(self):
        self.app_state_handlers = MagicMock()
        self.controller = JobTaskController(self.app_state_handlers)

    @patch("aoget.controller.job_task_controller.get_job_dao")
    def test_resolve_file_sizes_with_known_size(self, mock_get_job_dao):
        job_name = "Test Job"
        job = MagicMock()
        job.selected_files_count = 5
        job.selected_files_with_known_size = 0
        mock_get_job_dao.return_value.get_job_by_name.return_value = job
        self.app_state_handlers.db_lock = MagicMock()
        self.app_state_handlers.db_lock.__enter__ = MagicMock()
        self.app_state_handlers.db_lock.__exit__ = MagicMock()
        self.app_state_handlers.cache.is_cached_job = MagicMock(return_value=True)
        self.app_state_handlers.cache.get_files_of_job = MagicMock(
            return_value=[MagicMock(size_bytes=None) for _ in range(5)]
        )
        downloads = MagicMock()
        downloads.is_running_for_job = MagicMock(return_value=True)
        downloader = MagicMock()
        downloader.is_resolving_file_sizes = MagicMock(return_value=False)

        downloads.get_downloader.return_value = downloader
        self.app_state_handlers.downloads = downloads
        self.controller.resolve_file_sizes(job_name)
        # downloader.resolve_file_sizes.assert_called_once()

    def test_is_size_resolver_running(self):
        job_name = "Test Job"
        self.app_state_handlers.downloads.is_running_for_job = MagicMock(
            return_value=True
        )
        self.app_state_handlers.downloads.get_downloader = MagicMock()
        self.app_state_handlers.downloads.get_downloader.return_value.is_resolving_file_sizes = MagicMock(
            return_value=True
        )
        result = self.controller.is_size_resolver_running(job_name)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
