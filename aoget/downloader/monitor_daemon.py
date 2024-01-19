import threading

from model.job_monitor import JobMonitor, FILE_DOWNLOAD_PROGRESS, FILE_DOWNLOAD_STATUS


class MonitorDaemon:
    """A thread-safe progress reporter that reports progress of multiple event sources - firing on
    different threads - on a single thread. Also implements throttling of progress updates to
    avoid stale updates from being reported."""

    __job_monitor = None
    __lock = threading.Lock()
    __per_file_updates = {}

    def __init__(self, job_monitor: JobMonitor = None):
        """Create a progress reporter.
        :param job_monitor:
            The job monitor to report progress to. If None, no progress will be reported."""
        if job_monitor is None:
            return
        self.__job_monitor = job_monitor
        self.__lock = threading.Lock()
        flush_thread = threading.Thread(target=self.__update_observers, daemon=True)
        flush_thread.start()

    def __update_observers(self) -> None:
        """Update the observers with the current progress."""
        if self.__job_monitor is None:
            return
        with self.__lock:
            for filename, update in self.__per_file_updates.items():
                status = update[FILE_DOWNLOAD_STATUS]
                written, total = update[FILE_DOWNLOAD_PROGRESS]
                self.__job_monitor.on_download_progress_update(filename, written, total)
                self.__job_monitor.on_file_status_update(filename, status)
            self.__per_file_progress = {}  # Clear the updates after reporting

    def update_download_progress(self, filename: str, written: int, total: int) -> None:
        """Update the progress of the given filename.
        :param filename:
            The filename to update
        :param written:
            Bytes written so far
        :param total:
            Total bytes to write"""
        if self.__job_monitor is None:
            return
        with self.__lock:
            self.__per_file_progress[filename][FILE_DOWNLOAD_STATUS] = (written, total)

    def update_file_status(self, filename: str, status: str) -> None:
        """Update the status of the given filename.
        :param filename:
            The filename to update
        :param status:
            The status to update"""
        if self.__job_monitor is None:
            return
        with self.__lock:
            self.__per_file_progress[filename][FILE_DOWNLOAD_STATUS] = status
