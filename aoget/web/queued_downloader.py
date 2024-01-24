"""A queue for downloading files in a job. """

import os
import logging
import queue
import threading
from model.job import Job
from .downloader import download_file, ProgressObserver
from model.file_model import FileModel
from aoget.util.aogetutil import timestamp_str
from .monitor_daemon import MonitorDaemon

logger = logging.getLogger(__name__)


class FileProgressObserver(ProgressObserver):
    """A progress observer that binds to a file and reports progress to a MonitorDaemon."""

    filename = ""
    monitor = None

    def __init__(self, jobname: str, filename: str, monitor: MonitorDaemon):
        """Create a progress observer that binds to a monitor daemon.
        :param jobname:
            The name of the job to report progress for
        :param filename:
            The filename to report progress for
        :param monitor:
            The monitor to report progress to"""
        self.jobname = jobname
        self.filename = filename
        self.monitor = monitor

    def on_update_progress(self, written: int, total: int) -> None:
        """Report progress to the monitor daemon.
        :param written:
            The number of bytes written
        :param total:
            The total number of bytes to write"""
        self.monitor.update_download_progress(
            self.jobname, self.filename, written, total
        )


class QueuedDownloader:
    """A thread-safe queue for downloading files in a job. Intended to be created per job. 
    The dependency chain is as follows: JobDownloaderQueue -> JobDownloader -> Job -> FileModel"""

    job = None
    monitor = None
    worker_pool_size = 3
    queue = queue.Queue()
    threads = []

    def __init__(
        self,
        job: Job,
        monitor: MonitorDaemon = MonitorDaemon(),  # Blank monitor suppresses progress reporting
        worker_pool_size: int = 3,
    ):
        """Create a download queue for a job.
        :param job:
            The job to download
        :param monitor:
            The monitor to report progress to. Defaults to a blank monitor that suppresses
            progress reporting.
        :param worker_pool_size:
            The number of workers to use for downloading files. Defaults to 3."""
        self.job = job
        self.monitor = monitor
        self.worker_pool_size = worker_pool_size

    def run(self) -> None:
        """Run the download queue. Blocks until all files are downloaded."""
        self.__start_workers()
        self.__populate_queue()
        self.queue.join()
        self.__stop_workers()

    def start(self) -> None:
        """Start the download queue."""
        self.__start_workers()

    def stop(self) -> None:
        """Stop the download queue."""
        self.__stop_workers()

    def download_all(self) -> None:
        """Download all files in the job. Invoke once."""
        self.__populate_queue()

    def download_file(self, file: FileModel) -> None:
        """Download the given file.
        :param file:
            The file to download"""
        self.queue.put(file)

    def __start_workers(self, worker_pool=3):
        """Start the workers as per the worker pool size."""
        for i in range(worker_pool):
            t = threading.Thread(target=self.__download_worker)
            t.start()
            self.threads.insert(i, t)

    def __stop_workers(self) -> None:
        """Stop the workers by putting None (poison pill) on the queue and joining the threads"""
        for i in self.threads:
            self.queue.put(None)
        for t in self.threads:
            t.join()

    def __populate_queue(self):
        """Populate the queue with files to download."""
        for file in self.job.resolve_files_to_download():
            self.queue.put(file)

    def __download_worker(self):
        """The worker thread that downloads files from the queue."""
        while True:
            file_to_download = self.queue.get()
            if file_to_download is None:
                break
            logger.info("Worker took file: %s", file_to_download.name)
            try:
                self.__start_download(file_to_download)
            except Exception as e:
                logger.error("Worker failed with file: %s", file_to_download.name)
                logging.exception(e)
                self.__post_download(file_to_download, success=False, err=str(e))
            self.queue.task_done()

    def __start_download(self, file_to_download: FileModel) -> None:
        """Start the download of a file.
        :param file_to_download:
            The file to download"""
        file_to_download.status = FileModel.STATUS_DOWNLOADING
        file_to_download.add_event("Started downloading")
        download_file(
            file_to_download.url,
            os.path.join(self.job.target_folder, file_to_download.name),
            self.__create_download_observer_for(file_to_download.name),
        )
        logger.info("Worker finished with file: %s", file_to_download.name)
        self.__post_download(file_to_download, success=True)

    def __post_download(self, file: FileModel, success: bool, err: str = "") -> None:
        """Post download metadata update of a file.
        :param file:
            The file that was downloaded
        :param success:
            Whether the download was successful or not"""
        if success:
            file.status = FileModel.STATUS_DOWNLOADED
            file.add_event("Completed downloading")
        else:
            file.status = FileModel.STATUS_FAILED
            file.add_event("Failed downloading: " + err)

    def __create_download_observer_for(self, filename: str):
        """Create a progress observer for the given filename.
        :param filename:
            The filename to create the observer for
        :return:
            A progress observer"""
        logger.debug(
            "Creating download observer for job %s and file %s",
            self.job.name,
            filename,
        )
        return FileProgressObserver(self.job.name, filename, self.monitor)
