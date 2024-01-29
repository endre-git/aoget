import logging
from typing import Any
from model.job_monitor import JobMonitor


logger = logging.getLogger(__name__)


class MainWindowJobMonitor(JobMonitor):
    """Implementation of the JobMonitor interface that publishes events to the main window.
    To be created per-job."""

    file_bytes_written = {}

    def __init__(self, main_window_controller: Any, job_name: str):
        """Create a new job monitor."""
        self.main_window_controller = main_window_controller
        self.job_name = job_name

    def on_download_progress_update(
        self, filename: str, written: int, total: int
    ) -> None:
        """When the download progress is updated.
        :param filename:
            The name of the file being downloaded
        :param written:
            Bytes written so far locally.
        :param total:
            Size of the remote file."""
        percent_completed = 0 if total == 0 else int(written / total * 100)
        delta = 0
        eta_seconds = 0
        if filename in self.file_bytes_written:
            delta = written - self.file_bytes_written[filename]
            eta_seconds = int((total - written) / delta) if delta > 0 else 0
        self.file_bytes_written[filename] = written
        self.main_window_controller.update_file_download_progress(
            self.job_name, filename, written, percent_completed, delta, eta_seconds
        )

    def on_file_status_update(self, filename: str, status: str) -> None:
        """When the status of a file is updated.
        :param filename:
            The name of the file
        :param status:
            The new status of the file"""
        self.main_window_controller.update_file_status(self.job_name, filename, status)
