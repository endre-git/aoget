from typing import Any
from web.background_resolver import ResolverMonitor


class ResolverMonitorImpl(ResolverMonitor):
    """Implementation of the ResolverMonitor interface"""

    def __init__(
        self, main_window_data: Any, main_window: Any
    ) -> None:
        self.main_window = main_window
        self.main_window_data = main_window_data

    def on_resolved_file_size(self, job_name, file_name, size):
        """Called when the file size of a remote file has been resolved"""
        self.main_window.resolved_file_size_signal.emit(job_name, file_name, size)
        self.main_window_data.update_file_size(job_name, file_name, size)

    def on_all_file_size_resolved(self, job_name):
        """Called when all file sizes have been resolved"""
        self.main_window_data.on_resolver_finished(job_name)
