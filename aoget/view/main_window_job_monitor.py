import logging
from typing import Any
from model.job_monitor import JobMonitor
from aogetdb import get_file_model_dao


logger = logging.getLogger(__name__)


class MainWindowJobMonitor(JobMonitor):
    """Implementation of the JobMonitor interface that publishes events to the main window"""

    file_bytes_written = {}

    def __init__(self, main_window_data: Any, main_window: Any, job_name: str):
        """Create a new job monitor."""
        self.main_window = main_window
        self.main_window_data = main_window_data
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
        self.main_window.update_file_progress_signal.emit(
            self.job_name, filename, percent_completed, delta, eta_seconds
        )

    def on_file_status_update(self, filename: str, status: str) -> None:
        """When the status of a file is updated.
        :param filename:
            The name of the file
        :param status:
            The new status of the file"""
        file = self.main_window_data.jobs[self.job_name].get_file_by_name(filename)
        get_file_model_dao().update_file_model_status(file.id, status)
        self.main_window.update_file_status_signal.emit(
            self.job_name,
            filename,
            status,
            file.get_latest_history_timestamp(),
            file.get_latest_history_entry().event
        )
