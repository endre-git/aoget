"""A queue for downloading files in a job. """

import os
import logging
import queue
import threading
from model.job import Job
from .downloader import download_file, DownloadSignals
from model.file_model import FileModel
from .monitor_daemon import MonitorDaemon

logger = logging.getLogger(__name__)


class FileProgressSignals(DownloadSignals):
    """A progress observer that binds to a file and reports progress to a MonitorDaemon."""

    filename = ""
    monitor = None
    status_listeners = {}

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

    def on_update_status(self, status: str) -> None:
        """Report status to the monitor daemon.
        :param status:
            The new status"""
        self.monitor.update_file_status(self.jobname, self.filename, status)
        if status in self.status_listeners:
            listener = self.status_listeners.pop(status)
            listener.set()

    def register_status_listener(self, event: threading.Event, status: str) -> None:
        """Register a listener for a status update. If called multiple times, the last listener
        will be used.
        :param event:
            The event to invoke when the status is updated
        :param status:
            The status to listen to"""
        self.status_listeners[status] = event


class QueuedDownloader:
    """A thread-safe queue for downloading files in a job. Intended to be created per job.
    The dependency chain is as follows: JobDownloaderQueue -> JobDownloader -> Job -> FileModel
    """

    job = None
    monitor = None
    worker_pool_size = 3
    queue = queue.Queue()
    threads = []
    signals = {}
    files_in_queue = []
    files_downloading = []

    def __init__(
        self,
        job: Job,
        monitor: MonitorDaemon,  # Blank monitor suppresses progress reporting
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
        self.files_in_queue.append(file.name)
        self.queue.put(file)

    def register_listener(self, event, filename: str, status: str) -> None:
        """Register a listener for a file status update.
        :param event:
            The event to invoke when the status is updated
        :param filename:
            The name of the file to listen to
        :param status:
            The status to listen to"""
        if filename not in self.signals:
            raise ValueError("Unknown file: " + filename)
        self.signals[filename].register_status_listener(event, status)

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
            self.download_file(file)

    def __download_worker(self):
        """The worker thread that downloads files from the queue."""
        while True:
            try:
                file_to_download = self.queue.get()
                self.files_in_queue.remove(file_to_download.name)
                self.files_downloading.append(file_to_download.name)
                if file_to_download is None:
                    break
                logger.info("Worker took file: %s", file_to_download.name)
                try:
                    self.__start_download(file_to_download)
                except Exception as e:
                    logger.error("Worker failed with file: %s", file_to_download.name)
                    logging.exception(e)
                    self.__post_download(
                        file_to_download, new_status=FileModel.STATUS_FAILED, err=str(e)
                    )
                self.files_downloading.remove(file_to_download.name)
                self.queue.task_done()
            except Exception as e:
                # This is a catch-all exception handler to prevent the worker from dying
                logger.error("Unexpected error in worker: %s", e)

    def __start_download(self, file_to_download: FileModel) -> None:
        """Start the download of a file.
        :param file_to_download:
            The file to download"""
        file_to_download.status = FileModel.STATUS_DOWNLOADING
        file_to_download.add_event("Started downloading")
        signal = self.__create_download_signals_for(file_to_download.name)
        self.signals[file_to_download.name] = signal
        signal.on_update_status(FileModel.STATUS_DOWNLOADING)
        result_state = download_file(
            file_to_download.url,
            os.path.join(self.job.target_folder, file_to_download.name),
            signal,
        )
        logger.info("Worker finished with file: %s", file_to_download.name)
        self.__post_download(file_to_download, new_status=result_state)

    def __post_download(self, file: FileModel, new_status: str, err: str = "") -> None:
        """Post download metadata update of a file.
        :param file:
            The file that was downloaded
        :param success:
            Whether the download was successful or not"""
        file.status = new_status
        if new_status == FileModel.STATUS_COMPLETED:
            file.add_event("Completed downloading")
        elif new_status == FileModel.STATUS_STOPPED:
            file.add_event("Stopped downloading")
        elif new_status == FileModel.STATUS_FAILED:
            file.status = FileModel.STATUS_FAILED
            file.add_event("Failed downloading: " + err)
        self.signals[file.name].on_update_status(file.status)

    def __create_download_signals_for(self, filename: str):
        """Create a progress observer for the given filename.
        :param filename:
            The filename to create the observer for
        :return:
            A progress observer"""
        logger.debug(
            "Creating download signaler for job %s and file %s",
            self.job.name,
            filename,
        )
        return FileProgressSignals(self.job.name, filename, self.monitor)
