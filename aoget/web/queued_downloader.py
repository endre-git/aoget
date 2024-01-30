"""A queue for downloading files in a job. """

import os
import logging
import queue
import threading
from model.dto.job_dto import JobDTO
from .downloader import download_file, DownloadSignals, resolve_remote_file_size
from model.dto.file_model_dto import FileModelDTO
from model.file_model import FileModel
from .journal_daemon import JournalDaemon

logger = logging.getLogger(__name__)


class FileProgressSignals(DownloadSignals):
    """A progress observer that binds to a file and reports progress to a MonitorDaemon."""

    def __init__(self, jobname: str, filename: str, monitor: JournalDaemon):
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
        self.status_listeners = {}

    def on_update_progress(self, written: int, total: int) -> None:
        """Report progress to the monitor daemon.
        :param written:
            The number of bytes written
        :param total:
            The total number of bytes to write"""
        self.monitor.update_download_progress(
            self.jobname, self.filename, written, total
        )

    def on_update_status(self, status: str, err: str = None) -> None:
        """Report status to the monitor daemon.
        :param status:
            The new status"""
        self.monitor.update_file_status(self.jobname, self.filename, status, err=err)
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

    def on_event(self, event: str) -> None:
        """Report an event to the monitor daemon.
        :param event:
            The event to report"""
        self.monitor.add_file_event(self.jobname, self.filename, event)


class QueuedDownloader:
    """A thread-safe queue for downloading files in a job. Intended to be created per job."""

    def __init__(
        self,
        job: JobDTO,
        monitor: JournalDaemon,  # Blank monitor suppresses progress reporting
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
        self.monitor = monitor
        self.worker_pool_size = worker_pool_size
        self.queue = queue.Queue()
        self.threads = []
        self.signals = {}
        self.files_in_queue = []
        self.files_downloading = []
        self.size_resolver_lock = threading.RLock()
        self.is_resolver_running = False
        self.is_resolved_all_file_sizes = False
        self.resolved_file_sizes = {}
        self.download_thread_lock = threading.Lock()
        self.are_download_threads_running = False

    def run(self) -> None:
        """Run the download queue. Blocks until all files are downloaded."""
        self.__start_workers()
        self.__populate_queue()
        self.queue.join()
        self.__stop_workers()

    def start_download_threads(self) -> None:
        """Start the download queue."""
        with self.download_thread_lock:
            if not self.are_download_threads_running:
                self.__start_workers()
                self.are_download_threads_running = True

    def stop(self) -> None:
        """Stop the download queue."""
        self.__stop_workers()

    def download_file(self, file: FileModelDTO) -> None:
        """Download the given file.
        :param file:
            The file to download"""
        self.files_in_queue.append(file.name)
        self.queue.put(file)

    def cancel_download(self, filename: str) -> None:
        """Cancel the download of the given file.
        :param filename:
            The name of the file to cancel"""
        if filename in self.files_in_queue:
            self.files_in_queue.remove(filename)

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

    def is_resolving_file_sizes(self) -> bool:
        """Determine whether the file sizes are still being resolved.
        :return:
            True if the file sizes are still being resolved, False otherwise"""
        with self.size_resolver_lock:
            return self.is_resolver_running

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
        with self.download_thread_lock:
            self.are_download_threads_running = False

    def __download_worker(self):
        """The worker thread that downloads files from the queue."""
        while True:
            try:
                file_to_download = self.queue.get()
                if file_to_download is None:
                    break
                logger.info("Worker took file: %s", file_to_download.name)
                if file_to_download.name not in self.files_in_queue:
                    logger.info("File was cancelled before download started, not doing anything.")
                    self.queue.task_done()
                    continue
                self.files_in_queue.remove(file_to_download.name)
                self.files_downloading.append(file_to_download.name)

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
        signal = self.__create_download_signals_for(file_to_download.name)
        signal.on_update_status(FileModel.STATUS_DOWNLOADING)
        file_size = -1
        with self.size_resolver_lock:
            if file_to_download.name in self.resolved_file_sizes:
                file_size = self.resolved_file_sizes[file_to_download.name]
        result_state = download_file(
            file_to_download.url,
            os.path.join(self.job.target_folder, file_to_download.name),
            signal,
            file_size
        )
        logger.info("Worker finished with file: %s", file_to_download.name)
        self.__post_download(file_to_download, new_status=result_state)

    def __post_download(
        self, file: FileModel, new_status: str, err: str = None
    ) -> None:
        """Post download metadata update of a file.
        :param file:
            The file that was downloaded
        :param success:
            Whether the download was successful or not"""
        self.signals[file.name].on_update_status(new_status, err=err)
        self.signals.pop(file.name)

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
        signal = self.signals[filename] if filename in self.signals else None
        if signal is None:
            signal = FileProgressSignals(self.job.name, filename, self.monitor)
            self.signals[filename] = signal
        return signal

    def resolve_file_sizes(self, job_name: str, filemodels: list) -> None:
        """Resolve the file sizes of the given filemodels.
        :param job_name:
            The name of the job
        :param filemodels:
            The filemodels to resolve the file sizes for"""
        if self.is_resolving_file_sizes() or self.is_resolved_all_file_sizes:
            return

        def resolve_size_task():
            with self.size_resolver_lock:
                self.is_resolver_running = True

            logger.debug(
                "Resolving file sizes in background for %d files", len(filemodels)
            )
            for filemodel in filemodels:
                try:
                    filemodel.size_bytes = resolve_remote_file_size(filemodel.url)
                    self.monitor.update_file_size(
                        job_name, filemodel.name, filemodel.size_bytes
                    )
                    with self.size_resolver_lock:
                        self.resolved_file_sizes[filemodel.name] = filemodel.size_bytes
                except Exception as e:
                    logger.error(
                        "Failed to resolve file size for %s", filemodel.name, exc_info=e
                    )
            logger.debug(
                "Finished resolving file sizes in background for %d files",
                len(filemodels),
            )
            with self.size_resolver_lock:
                self.resolved_all_file_sizes = True
                self.is_resolver_running = False

        threading.Thread(target=resolve_size_task).start()
