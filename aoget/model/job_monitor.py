from abc import ABC, abstractmethod


class JobMonitor(ABC):
    """Abstract class for monitoring a job. Fires on change events (download progress,
    file status, job status)."""

    FILE_DOWNLOAD_PROGRESS = "file-download-progress"
    FILE_DOWNLOAD_STATUS = "file-download-status"

    @abstractmethod
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
        pass

    @abstractmethod
    def on_file_status_update(self, filename: str, status: str) -> None:
        """When the status of a file is updated.
        :param filename:
            The name of the file
        :param status:
            The new status of the file"""
        pass
