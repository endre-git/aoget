import unittest
from unittest.mock import MagicMock, patch

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
        self.controller.handlers.downloads.job_downloaders = {"test_job": job_downloader}
        with patch(
            "aoget.controller.main_window_controller.get_config_value"
        ) as mock_get_config_value:
            mock_get_config_value.return_value = 10
            self.controller.actualize_config()
            self.assertEqual(job_downloader.download_retry_attempts, 10)


if __name__ == "__main__":
    unittest.main()
