"""A queue for downloading files in a job. """

import time
import os
import logging
import threading
from model.job import Job
from model.dto.job_dto import JobDTO
from web.downloader import download_file, DownloadSignals, resolve_remote_file_size
from web.file_queue import FileQueue
from model.dto.file_model_dto import FileModelDTO
from model.file_model import FileModel
from controller.journal_daemon import JournalDaemon
from util.aogetutil import human_duration
from util.disk_util import get_local_file_size

logger = logging.getLogger(__name__)

SIZE_RESOLVER_ATTEMPTS = 10


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
        self.rate_limit_bps = 0
        self.cancelled = False

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
            logger.info(
                f"Signaled listener for status: {status} of filename {self.filename}"
            )

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
        self.queue = FileQueue()
        self.threads = []
        self.signals = {}
        self.files_in_queue = []
        self.files_downloading = []
        self.size_resolver_lock = threading.RLock()
        self.is_resolver_running = False
        self.is_resolved_all_file_sizes = False
        self.size_resolver_cancelled = False
        self.resolved_file_sizes = {}
        self.download_thread_lock = threading.Lock()
        self.are_download_threads_running = False
        self.active_thread_count = 0
        self.health_check_lock = threading.RLock()
        self.health_check_cancelled = False
        self.is_health_check_running = False
        self.is_resuming = False

    def run(self) -> None:
        """Run the download queue. Blocks until all files are downloaded."""
        self.__start_workers()
        self.__populate_queue()
        self.queue.join()
        self.__stop_workers(sync=True)

    def start_download_threads(self) -> None:
        """Start the download queue."""
        with self.download_thread_lock:
            if not self.are_download_threads_running:
                self.__start_workers()
                self.are_download_threads_running = True

    def stop(self) -> None:
        """Stop the download queue."""
        self.__stop_workers(sync=True)

    def shutdown(self) -> None:
        """Shutdown the download queue, stop running downloads, drop in-queue downloads.
        Stopped downloads won't get a normal status update to Stopped, this enables resuming
        the last state (Downloading) at next app start."""
        self.__stop_workers()
        self.health_check_cancelled = True
        self.size_resolver_cancelled = True
        self.files_in_queue.clear()
        if len(self.files_downloading) > 0:
            signals = self.signals.values()
            for signal in signals:
                signal.cancel(shutdown=True)

    def download_file(self, file: FileModelDTO) -> None:
        """Download the given file.
        :param file:
            The file to download"""
        self.files_in_queue.append(file.name)
        self.queue.put_file(file)
        self.monitor.update_file_status(
            self.job.name, file.name, FileModel.STATUS_QUEUED
        )

    def download_files(self, files: list) -> None:
        """Download the given files.
        :param files:
            The files to download"""
        self.files_in_queue.extend([file.name for file in files])
        self.queue.put_all(files)
        logger.info(f"Added {len(files)} files to the queue for job {self.job.name}")

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

    def is_checking_health(self) -> bool:
        """Determine whether the health check is still running.
        :return:
            True if the health check is still running, False otherwise"""
        with self.health_check_lock:
            return self.is_health_check_running

    def is_downloading(self) -> bool:
        """Determine whether the queue is still downloading files.
        :return:
            True if the queue is still downloading files, False otherwise"""
        return len(self.files_downloading) > 0 or len(self.files_in_queue) > 0

    def update_priority(self, file: FileModelDTO) -> None:
        """Update the priority of the given file.
        :param file:
            The file to update the priority for"""
        if file.name in self.files_in_queue:
            self.queue.put_file(file)

    def __start_workers(self):
        """Start the workers as per the worker pool size."""
        for i in range(self.worker_pool_size):
            t = threading.Thread(
                target=self.__download_worker,
                name=f"download-{self.job.name}-{i}-",
                daemon=True,
            )
            t.start()
            self.threads.insert(i, t)

    def __stop_workers(self, sync=False) -> None:
        """Stop the workers by putting None (poison pill) on the queue and joining the threads"""
        for i in self.threads:
            self.queue.poison_pill()
        if sync:
            for t in self.threads:
                t.join()
        with self.download_thread_lock:
            self.are_download_threads_running = False

    def __download_worker(self):
        """The worker thread that downloads files from the queue."""
        while True:
            try:
                file_to_download = self.queue.pop_file()
                if FileQueue.is_poison_pill(file_to_download):
                    logger.debug("Worker received poison pill, stopping.")
                    return
                logger.debug("Worker took file: %s", file_to_download.name)
                if file_to_download.name not in self.files_in_queue:
                    logger.debug(
                        "File was cancelled before download started, not doing anything."
                    )
                    self.queue.task_done()
                    continue
                self.files_in_queue.remove(file_to_download.name)
                self.files_downloading.append(file_to_download.name)

                with self.download_thread_lock:
                    self.active_thread_count += 1
                try:
                    self.__start_download(file_to_download)
                except Exception as e:
                    logger.error("Worker failed with file: %s", file_to_download.name)
                    logging.exception(e)
                    self.__post_download(
                        file_to_download, new_status=FileModel.STATUS_FAILED, err=str(e)
                    )
                with self.download_thread_lock:
                    self.active_thread_count -= 1
                self.files_downloading.remove(file_to_download.name)
                self.queue.task_done()

            except Exception as e:
                # This is a catch-all exception handler to prevent the worker from dying
                logger.error("Unexpected error in worker: %s", e)
                logger.exception(e)

    def get_active_thread_count(self) -> int:
        """Get the number of active threads.
        :return:
            The number of active threads"""
        with self.download_thread_lock:
            return self.active_thread_count

    def add_thread(self) -> None:
        """Add a thread to the worker pool."""
        self.worker_pool_size += 1
        t = threading.Thread(
            target=self.__download_worker,
            name=f"download-{self.job.name}-{len(self.threads)}-",
            daemon=True,
        )
        t.start()
        self.threads.append(t)

    def remove_thread(self) -> None:
        """Kill a thread from the worker pool."""
        self.worker_pool_size -= 1
        if len(self.threads) > 1:
            self.queue.poison_pill()

    def set_rate_limit(self, rate_limit_bps: int) -> None:
        """Set the rate limit for the downloaders.
        :param rate_limit_bps:
            The rate limit in bytes per second"""
        for signal in self.signals.values():
            signal.set_rate_limit(rate_limit_bps)

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
            file_size,
        )
        logger.debug("Worker finished with file: %s", file_to_download.name)
        self.__post_download(file_to_download, new_status=result_state)

    def __target_path_of_file(self, file_model_dto):
        if self.job is None:
            raise ValueError(
                f"Job is not set, can't determine file target path for {file_model_dto.name}"
            )
        return os.path.join(self.job.target_folder, file_model_dto.name)

    def __post_download(
        self, file: FileModel, new_status: str, err: str = None
    ) -> None:
        """Post download metadata update of a file.
        :param file:
            The file that was downloaded
        :param success:
            Whether the download was successful or not"""
        signals = self.signals[file.name]
        if new_status == FileModel.STATUS_STOPPED and signals.shutdown:
            self.monitor.add_file_event(
                self.job.name, file.name, "Stopped due to app shutdown."
            )
        else:
            signals.on_update_status(new_status, err=err)
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

    def __requeue_queued_files(self, job_name: str, files: list) -> None:
        """Re-queue files that were queued at the last app run. Invoked once, when the app starts."""
        files_to_queue = []
        events = {}
        for file in files.values():
            if file.status == FileModel.STATUS_QUEUED:
                logger.debug(
                    "File %s was queued at last app run, will re-queue now.",
                    file.name,
                )
                files_to_queue.append(file)
                events[file.name] = "Re-queued after app-restart."
        self.download_files(files_to_queue)
        self.monitor.add_file_events(job_name, events)

    def resume_files(self, files: list, file_controller: any, callback: any) -> None:
        """Resume files as per the last app run. Invoked once, when the app starts."""
        job_name = self.job.name

        def resume_task():
            self.is_resuming = True
            t0 = time.time()
            logger.info("Resuming files for job %s", job_name)
            callback.emit(job_name, Job.RESUME_STARTING, "")
            try:
                # there might be some "remnant stopping" states if the app
                # crashed / was killed, so set them all to Stopped
                t1 = time.time()
                for file in files.values():
                    if file.status == FileModel.STATUS_STOPPING:
                        logger.debug(
                            "File %s was stopping at last app run, will set to Stopped.",
                            file.name,
                        )
                        self.monitor.update_file_status(
                            job_name, file.name, FileModel.STATUS_STOPPED
                        )
                logger.info(
                    "Finished setting stopping files to Stopped in %s",
                    human_duration(time.time() - t1),
                )
                t1 = time.time()

                for file in files.values():
                    if file.status == FileModel.STATUS_DOWNLOADING:
                        logger.debug(
                            "File %s was downloaded at last app run, will resume now.",
                            file.name,
                        )
                        self.monitor.add_file_event(
                            job_name, file.name, "Resumed after app-restart."
                        )
                        file_controller.start_download(job_name, file.name)
                logger.info(
                    "Finished resuming downloading files for job %s in %s",
                    job_name,
                    human_duration(time.time() - t1),
                )
                t1 = time.time()

                # optimization: queued files can be numerous, so we batch-process them
                self.__requeue_queued_files(job_name, files)
                logger.info(
                    "Finished re-queuing files for job %s in %s",
                    job_name,
                    human_duration(time.time() - t1),
                )
                t1 = time.time()

                for file in files.values():
                    if file.status == FileModel.STATUS_COMPLETED:
                        local_size = get_local_file_size(file.target_path)
                        if local_size is None:
                            raise ValueError(
                                f"Local file size is not set for {file.name}"
                            )
                        if file.downloaded_bytes is None:
                            logger.error(
                                """Database apparently corrupted for file "%s",
                                downloaded_bytes unset, despite marked as complete.""",
                                file.name,
                            )
                            continue
                        if local_size == -1:
                            file.status = FileModel.STATUS_INVALID
                            self.monitor.add_file_event(
                                job_name, file.name, "Local file is missing."
                            )
                        elif local_size < file.downloaded_bytes:
                            file.status = FileModel.STATUS_INVALID
                            self.monitor.add_file_event(
                                job_name,
                                file.name,
                                "Local file corrupted (smaller than expected).",
                            )
                callback.emit(job_name, Job.RESUME_SUCCESS, "")
                logger.info(
                    "Finished checking local files for job %s in %s",
                    job_name,
                    human_duration(time.time() - t1),
                )

            except Exception as e:
                logger.error("Failed to resume files for job %s", job_name, exc_info=e)
                callback.emit(job_name, Job.RESUME_FAILED, e.msg)

            logger.info(
                "Finished resuming files for job %s in %s",
                job_name,
                human_duration(time.time() - t0),
            )
            self.is_resuming = False

        threading.Thread(target=resume_task, name=f"resume-files-{job_name}").start()

    def health_check(self, filemodels: list, callback: any) -> None:
        """Check the health of the given filemodels.
        :param job_name:
            The name of the job
        :param filemodels:
            The filemodels to check the health for"""
        if self.is_checking_health():
            return

        def health_check_task():
            t0 = time.time()
            with self.health_check_lock:
                self.is_health_check_running = True

            job_name = self.job.name
            logger.debug("Checking health in background for %d files", len(filemodels))
            success = 0
            failure = 0
            skipped = 0
            crashed = 0
            files_indeed_done = 0
            total_size_local = 0
            for filemodel in filemodels:
                if self.health_check_cancelled:
                    return
                try:
                    local_path = self.__target_path_of_file(filemodel)
                    local_size = (
                        os.path.getsize(local_path) if os.path.isfile(local_path) else 0
                    )
                    total_size_local += local_size
                    # if completed, assumed size must match size on disk
                    if filemodel.status == FileModel.STATUS_COMPLETED:
                        if filemodel.size_bytes != local_size:
                            self.monitor.update_file_status(
                                job_name,
                                filemodel.name,
                                FileModel.STATUS_INVALID,
                                err="Size mismatch despite Completed state.",
                            )
                            self.monitor.update_download_progress(
                                job_name,
                                filemodel.name,
                                local_size,
                                filemodel.size_bytes,
                            )
                            failure += 1
                        else:
                            success += 1
                            files_indeed_done += 1
                    # if has downloaded bytes, disk should match
                    elif (
                        filemodel.status != FileModel.STATUS_DOWNLOADING
                        and filemodel.downloaded_bytes
                        and filemodel.downloaded_bytes > 0
                    ):
                        if filemodel.downloaded_bytes != local_size:
                            self.monitor.update_file_status(
                                job_name,
                                filemodel.name,
                                FileModel.STATUS_INVALID,
                                err="Size mismatch for ongoing download.",
                            )
                            if filemodel.size_bytes > 0:
                                self.monitor.update_download_progress(
                                    job_name,
                                    filemodel.name,
                                    local_size,
                                    filemodel.size_bytes,
                                )
                            failure += 1
                        else:
                            success += 1
                    else:
                        skipped += 1
                except Exception as e:
                    logger.error(
                        "Failed to do an integrity check for %s",
                        filemodel.name,
                        exc_info=e,
                    )
                    self.monitor.update_file_status(
                        job_name,
                        filemodel.name,
                        FileModel.STATUS_FAILED,
                        err="Failed integrity check: " + str(e),
                    )
                    crashed += 1

            # the following won't work in the current approach since
            # actively downloading files are not checked
            # self.monitor.update_job_downloaded_bytes(job_name, total_size_local)
            self.monitor.update_job_files_done(job_name, files_indeed_done)

            logger.debug(
                "Finished checking health in background for %d files",
                len(filemodels),
            )
            with self.health_check_lock:
                self.is_health_check_running = False

            report = ""
            report += f"Finished integrity check for job {job_name} in {human_duration(time.time() - t0)}.<br/>"
            report += f"<b>{success} file(s) passed, {failure} failed, {skipped} skipped.</b><br/>"
            report += "(Active downloads and files not yet started are skipped by design.)<br/>"
            if crashed > 0:
                report += f"For {crashed} file(s) the integrity checking process crashed.<br/>"
            report += """</p><p>Individual results are available in the files table,
                         filter for <b>Failed</b> or <b>Invalid</b> status.</p>"""

            callback.emit("Integrity Check Complete", report)

        threading.Thread(
            target=health_check_task, name=f"health-check-{self.job.name}"
        ).start()

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

            attempt = 1
            had_failures = True
            while attempt < SIZE_RESOLVER_ATTEMPTS and had_failures:

                had_failures = False
                logger.debug(
                    "Resolving file sizes in background for %d files", len(filemodels)
                )
                for filemodel in filemodels:
                    if self.size_resolver_cancelled:
                        return
                    if filemodel.size_bytes is not None and filemodel.size_bytes > 0:
                        continue
                    try:
                        filemodel.size_bytes = resolve_remote_file_size(filemodel.url)
                        self.monitor.update_file_size(
                            job_name, filemodel.name, filemodel.size_bytes
                        )
                        with self.size_resolver_lock:
                            self.resolved_file_sizes[filemodel.name] = (
                                filemodel.size_bytes
                            )
                    except Exception as e:
                        logger.error(
                            "Failed to resolve file size for %s",
                            filemodel.name,
                            exc_info=e,
                        )
                        self.monitor.add_file_event(
                            job_name, filemodel.name, "Size resolver failed: " + str(e)
                        )
                        had_failures = True
                    attempt += 1
                    logger.debug(
                        "Size resolver attempt %d for job %s finished with sucess: %b",
                        attempt,
                        job_name,
                        not had_failures,
                    )
            logger.debug(
                "Finished resolving file sizes in background for %d files of job %s",
                len(filemodels),
                job_name,
            )
            with self.size_resolver_lock:
                self.resolved_all_file_sizes = True
                self.is_resolver_running = False

        threading.Thread(
            target=resolve_size_task, name=f"size-resolver-{self.job.name}"
        ).start()
