from abc import ABC, abstractmethod
from threading import Thread
import logging
from aoget.web.downloader import resolve_remote_file_size

logger = logging.getLogger(__name__)


class ResolverMonitor(ABC):
    @abstractmethod
    def on_resolved_file_size(self, url: str, size_bytes: int) -> None:
        pass

    @abstractmethod
    def on_all_file_size_resolved(self, job_name: str) -> None:
        pass


class BackgroundResolver:
    """Class for resolving file sizes and other metadata in the background."""

    def resolve_file_sizes(self,
                           job_name: str,
                           filemodels: list,
                           resolver_monitor: ResolverMonitor) -> None:
        """Resolve the file sizes of the given filemodels.
        :param job_name:
            The name of the job
        :param filemodels:
            The filemodels to resolve the file sizes for"""
        def resolve_size_task():
            logger.debug("Resolving file sizes in background for %d files", len(filemodels))
            for filemodel in filemodels:
                filemodel.size_bytes = resolve_remote_file_size(filemodel.url)
                resolver_monitor.on_resolved_file_size(filemodel.url, filemodel.size_bytes)
            logger.debug("Finished resolving file sizes in background for %d files",
                         len(filemodels))
            resolver_monitor.on_all_file_size_resolved(job_name)
        Thread(target=resolve_size_task).start()
