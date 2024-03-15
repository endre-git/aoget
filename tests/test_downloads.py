import unittest
from unittest.mock import MagicMock, patch
from aoget.controller.downloads import Downloads
from aoget.model.job import Job


class TestDownloads(unittest.TestCase):

    def setUp(self):
        self.app_state_handlers_mock = MagicMock()
        self.downloads = Downloads(self.app_state_handlers_mock)

    def test_init(self):
        self.assertEqual(self.downloads.app, self.app_state_handlers_mock)
        self.assertEqual(self.downloads.job_downloaders, {})
        self.assertTrue(self.downloads.start_download_threads)

    @patch("aoget.controller.downloads.get_job_dao")
    def test_get_downloader(self, mock_get_job_dao):
        test_job = Job(
            id=100,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        mock_get_job_dao.return_value.get_job_by_name.return_value = test_job

        job_name = "test_job"
        self.downloads.get_downloader(job_name)
        self.assertTrue(job_name in self.downloads.job_downloaders)

    @patch("aoget.controller.downloads.get_job_dao")
    def test_get_allocated_thread_count_job_not_running(self, mock_get_job_dao):
        test_job = Job(
            id=100,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
            threads_allocated=2,
        )
        mock_get_job_dao.return_value.get_job_by_name.return_value = test_job
        job_name = "test_job"
        thread_count = self.downloads.get_allocated_thread_count(job_name)
        assert thread_count == 2

    @patch("aoget.controller.downloads.get_job_dao")
    def test_get_allocated_thread_count_job_running(self, mock_get_job_dao):
        test_job = Job(
            id=100,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
            threads_allocated=2,
        )
        mock_get_job_dao.return_value.get_job_by_name.return_value = test_job
        job_name = "test_job"
        self.downloads.get_downloader(job_name)  # setup downloader
        thread_count = self.downloads.get_allocated_thread_count(job_name)
        assert thread_count == 2

    def test_get_active_thread_count_job_not_running(self):
        thread_count = self.downloads.get_active_thread_count("test_job")
        assert thread_count == 0

    @patch("aoget.controller.downloads.get_job_dao")
    def test_get_active_thread_count_job_running(self, mock_get_job_dao):
        test_job = Job(
            id=100,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
            threads_allocated=2,
        )
        mock_get_job_dao.return_value.get_job_by_name.return_value = test_job
        downloader = self.downloads.get_downloader("test_job")
        downloader.files_downloading = ["file1"]
        downloader.active_thread_count = 1
        thread_count = self.downloads.get_active_thread_count("test_job")
        assert thread_count == 1  # would be 2, but none running in test

    def test_download_files(self):
        job_name = "test_job"
        file_dtos = ["file1", "file2"]
        downloader = MagicMock()
        self.downloads.get_downloader = MagicMock(return_value=downloader)
        self.downloads.download_files(job_name, file_dtos)
        downloader.download_files.assert_called_with(file_dtos)

    def test_download_file(self):
        job_name = "test_job"
        file_dto = MagicMock()
        downloader = MagicMock()
        self.downloads.get_downloader = MagicMock(return_value=downloader)
        self.downloads.download_file(job_name, file_dto)
        downloader.download_file.assert_called_with(file_dto)

    def test_shutdown_all(self):
        downloader = MagicMock()
        self.downloads.job_downloaders = {"test_job": downloader}
        self.downloads.shutdown_all()
        downloader.shutdown.assert_called()

    def test_shutdown_for_job(self):
        downloader = MagicMock()
        self.downloads.job_downloaders = {"test_job": downloader}
        self.downloads.shutdown_for_job("test_job")
        downloader.shutdown.assert_called()

    def test_set_retry_attempts(self):
        self.downloads.set_retry_attempts(9)
        for downloader in self.downloads.job_downloaders.values():
            downloader.set_retry_attempts.assert_called_with(9)

    def test_dequeue_files(self):
        job_name = "test_job"
        file_dtos = ["file1", "file2"]
        downloader = MagicMock()
        self.downloads.get_downloader = MagicMock(return_value=downloader)
        self.downloads.dequeue_files(job_name, file_dtos)
        downloader.dequeue_files.assert_called_with(file_dtos)

    def test_stop_active_downloads(self):
        job_name = "test_job"
        file_dtos = ["file1", "file2"]
        downloader = MagicMock()
        self.downloads.get_downloader = MagicMock(return_value=downloader)
        self.downloads.stop_active_downloads(job_name, file_dtos)
        downloader.stop_active_downloads.assert_called_with(file_dtos)

    def test_is_job_resuming(self):
        job_name = "test_job"
        downloader = MagicMock()
        self.downloads.job_downloaders = {"test_job": downloader}
        downloader.is_resuming = True
        self.assertEqual(True, self.downloads.is_job_resuming(job_name))

    def test_is_job_downloading(self):
        job_name = "test_job"
        downloader = MagicMock()
        self.downloads.job_downloaders = {"test_job": downloader}
        downloader.is_downloading.return_value = True
        self.assertEqual(True, self.downloads.is_job_downloading(job_name))

    def test_is_job_size_resolving(self):
        job_name = "test_job"
        downloader = MagicMock()
        self.downloads.job_downloaders = {"test_job": downloader}
        downloader.is_resolving_file_sizes.return_value = True
        self.assertEqual(True, self.downloads.is_job_size_resolving(job_name))


if __name__ == '__main__':
    unittest.main()
