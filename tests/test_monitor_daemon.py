import unittest
from collections import defaultdict
from aoget.web.monitor_daemon import MonitorDaemon
from time import sleep


class MockJobMonitor:
    def __init__(self):
        self.file_updates = defaultdict(dict)

    def on_file_status_update(self, filename, status):
        self.file_updates[filename]["status"] = status

    def on_download_progress_update(self, filename, written, total):
        self.file_updates[filename]["progress"] = (written, total)


class TestMonitorDaemon(unittest.TestCase):

    def test_monitor_daemon(self):
        # Setup
        job_name = "test_job"
        filename = "test_file.txt"
        mock_monitor = MockJobMonitor()
        daemon = MonitorDaemon(update_interval_seconds=0.01)

        # Add job monitor
        daemon.add_job_monitor(job_name, mock_monitor)

        # Simulate file download progress and status updates
        daemon.update_download_progress(job_name, filename, 100, 1000)
        daemon.update_file_status(job_name, filename, "downloading")

        # Allow some time for the daemon to process updates
        sleep(0.1)

        # Test if updates are processed correctly
        self.assertIn(filename, mock_monitor.file_updates)
        self.assertEqual(mock_monitor.file_updates[filename]["progress"], (100, 1000))
        self.assertEqual(mock_monitor.file_updates[filename]["status"], "downloading")

        # Cleanup
        daemon.stop()


if __name__ == "__main__":
    unittest.main()
