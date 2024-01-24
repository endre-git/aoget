import threading
import time
import logging
from collections import defaultdict
from model.job_monitor import JobMonitor

logger = logging.getLogger(__name__)


class MonitorDaemon:
    """A thread-safe progress reporter that reports progress of multiple event sources - firing on
    different threads - on a single thread. Also implements throttling of progress updates to
    avoid stale update reporting."""

    __job_monitors = {}
    __lock = threading.Lock()
    __updates = defaultdict(lambda: defaultdict(dict))
    __stopped = False

    def __init__(self, update_interval_seconds: int = 1):
        """Create a progress reporter.
        :param job_monitor:
            The job monitor to report progress to. If None, no progress will be reported.
        """
        self.update_interval_seconds = update_interval_seconds
        self.__lock = threading.Lock()
        flush_thread = threading.Thread(target=self.__update_observers, daemon=True)
        flush_thread.start()

    def __report_file_update(self, job_monitor: JobMonitor, filename: str, update: dict) -> None:
        """Report a file update to a specific job monitor.
        :param job_monitor:
            The job monitor to report to
        :param filename:
            The filename to report
        :param update:
            The update to report"""
        if JobMonitor.FILE_DOWNLOAD_STATUS in update:
            status = update[JobMonitor.FILE_DOWNLOAD_STATUS]
            job_monitor.on_file_status_update(filename, status)
            del update[JobMonitor.FILE_DOWNLOAD_STATUS]
        if JobMonitor.FILE_DOWNLOAD_PROGRESS in update:
            written, total = update[
                JobMonitor.FILE_DOWNLOAD_PROGRESS
            ]
            job_monitor.on_download_progress_update(
                filename, written, total
            )
            del update[JobMonitor.FILE_DOWNLOAD_PROGRESS]

    def __update_observers(self) -> None:
        """Update the observers with the current progress."""
        while not self.__stopped:
            if len(self.__job_monitors) > 0 and len(self.__updates) > 0:
                with self.__lock:
                    for jobname, job_files in self.__updates.items():
                        if jobname in self.__job_monitors:
                            job_monitor = self.__job_monitors[jobname]
                            for filename, update in job_files.items():
                                self.__report_file_update(job_monitor, filename, update)
                    self.__updates = defaultdict(
                        lambda: defaultdict(dict)
                    )  # Clear the updates after reporting
            time.sleep(self.update_interval_seconds)

    def add_job_monitor(self, job_name: str, job_monitor: JobMonitor) -> None:
        """Add a job monitor to the progress reporter.
        :param job_name:
            The name of the job
        :param job_monitor:
            The job monitor to add"""
        self.__job_monitors[job_name] = job_monitor

    def remove_job_monitor(self, job_name: str) -> None:
        """Remove a job monitor from the progress reporter.
        :param job_name:
            The name of the job"""
        if job_name in self.__job_monitors:
            del self.__job_monitors[job_name]

    def update_download_progress(
        self, jobname: str, filename: str, written: int, total: int
    ) -> None:
        """Update the progress of the given filename.
        :param jobname:
            The name of the job
        :param filename:
            The filename to update
        :param written:
            Bytes written so far
        :param total:
            Total bytes to write"""
        if len(self.__job_monitors) == 0:
            return
        with self.__lock:
            self.__updates[jobname][filename][JobMonitor.FILE_DOWNLOAD_PROGRESS] = (
                written,
                total,
            )

    def update_file_status(self, jobname: str, filename: str, status: str) -> None:
        """Update the status of the given filename.
        :param jobname:
            The name of the job
        :param filename:
            The filename to update
        :param status:
            The status to update"""
        if len(self.__job_monitors) == 0:
            return
        with self.__lock:
            self.__updates[jobname][filename][JobMonitor.FILE_DOWNLOAD_STATUS] = status

    def stop(self):
        """Stop the progress reporter."""
        self.__stopped = True
