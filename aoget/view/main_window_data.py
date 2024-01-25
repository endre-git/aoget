import os
import logging
from typing import Any
from threading import Event
from .main_window_job_monitor import MainWindowJobMonitor
from web.monitor_daemon import MonitorDaemon
from web.queued_downloader import QueuedDownloader
from aogetdb import get_job_dao, get_file_model_dao
from .resolver_monitor_impl import ResolverMonitorImpl
from web.background_resolver import BackgroundResolver
from model.file_model import FileModel
from model.job import Job

logger = logging.getLogger(__name__)


class MainWindowData:
    """Data class for the main window. Implements data binds beetween the UI and the underlying
    models."""

    jobs = {}
    active_resolvers = {}
    download_queues = {}
    download_monitors = {}

    FILE_DELETION_WAIT_SECONDS = 5

    def __init__(self, main_window: Any):
        self.main_window = main_window
        self.monitor_daemon = MonitorDaemon()

    def load_jobs(self) -> None:
        """Load jobs from the database"""
        jobs = get_job_dao().get_all_jobs()
        for job in jobs:
            self.jobs[job.name] = job
        self.__validate_file_states()

    def job_count(self) -> int:
        """Get the number of jobs"""
        return len(self.jobs)

    def get_job_by_name(self, name) -> Job:
        """Get a job by its name"""
        return self.jobs[name] or None

    def get_jobs(self):
        """Get all jobs"""
        return self.jobs.values()

    def job_post_select(self, job_name: str) -> None:
        """Called after a job has been selected"""
        self.__resolve_file_sizes(job_name)

    def add_job(self, job) -> None:
        """Add a job"""
        self.jobs[job.name] = job
        get_job_dao().add_job(job)
        self.__resolve_file_sizes(job.name)

    def update_file_size(self, job_name, file_name, size):
        """Update the size of a file"""
        for job_name in self.jobs.keys():
            for file in self.jobs[job_name].files:
                if file.name == file_name:
                    file.size_bytes = size
                    get_file_model_dao().update_file_model_size(file.id, size)

    def resolve_file_url(self, job_name: str, file_name: str) -> str:
        """Resolve the URL of a file"""
        if job_name not in self.jobs:
            return ""
        return self.jobs[job_name].get_file_by_name(file_name).url

    def resolve_local_file_path(self, job_name: str, file_name: str) -> str:
        """Resolve the local file path of a file"""
        if job_name not in self.jobs:
            return ""
        return self.jobs[job_name].get_file_by_name(file_name).get_target_path()

    def redownload_file(self, job_name: str, file_name: str) -> (bool, str):
        """Redownload the given file
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :return:
            A tuple containing a boolean indicating whether the download was started successfully
            and a string containing the status of the file or the error message if download
            could not be started"""
        if self.download_queues.get(job_name) is None:
            return self.start_download(job_name, file_name)
        if file_name in self.download_queues[job_name].files_in_queue:
            return True, "File is already downloading or queued."
        stopped_event = Event()
        if file_name in self.download_queues[job_name].files_downloading:
            # stop the current download and wait for it to conclude
            could_stop, msg = self.stop_download(
                job_name, file_name, stopped_event
            )
            if not could_stop:
                return False, msg
            stopped_event.wait(self.FILE_DELETION_WAIT_SECONDS)
        # delete file from disk
        try:
            file = self.jobs[job_name].get_file_by_name(file_name)
            if os.path.exists(file.get_target_path()):
                os.remove(file.get_target_path())
            # reset downloaded bytes
            file.downloaded_bytes = 0
            self.download_queues[job_name].signals[file_name].on_update_progress(
                0, file.size_bytes
            )
        except Exception as e:
            logger.error("Could not delete file from disk: %s", e)
            return False, "Could not delete file from disk."
        return self.start_download(job_name, file_name)

    def __resolve_file_sizes(self, job_name: str) -> None:
        """Resolve the file sizes of all selected files that have an unknown size"""
        if self.active_resolvers.get(job_name) is not None:
            logger.debug("Resolver for job %s is already running", job_name)
            return
        self.active_resolvers[job_name] = 'running'
        BackgroundResolver().resolve_file_sizes(
            job_name,
            self.jobs[job_name].get_selected_files_with_unknown_size(),
            ResolverMonitorImpl(self, self.main_window),
        )

    def __validate_file_states(self) -> None:
        """Validate the file states"""
        for job in self.jobs.values():
            for file in job.files:
                if file.status == FileModel.STATUS_DOWNLOADING:
                    logger.info(
                        "File %s was downloaded at last app run, will resume now.",
                        file.name,
                    )
                    file.add_event("Resumed after app-restart.")
                    self.start_download(job.name, file.name)
                    get_file_model_dao().update_file_model_status(file.id, file.status)

            for file in job.files:
                if file.status == FileModel.STATUS_QUEUED:
                    logger.info(
                        "File %s was queued at last app run, will re-queue now.",
                        file.name,
                    )
                    file.add_event("Re-queued after app-restart.")
                    self.start_download(job.name, file.name)
                    get_file_model_dao().update_file_model_status(file.id, file.status)

            for file in job.files:
                if file.status == FileModel.STATUS_COMPLETED:
                    local_size = file.validate_downloaded()
                    if local_size == -1:
                        file.status = FileModel.STATUS_INVALID
                        file.add_event("Local file does not exist.")
                        get_file_model_dao().update_file_model_status(
                            file.id, file.status
                        )
                    elif local_size < file.downloaded_bytes:
                        file.status = FileModel.STATUS_INVALID
                        file.add_event("Local file might be corrupted.")
                        get_file_model_dao().update_file_model_status(
                            file.id, file.status
                        )

    def on_resolver_finished(self, job_name: str) -> None:
        """Called when a resolver has finished"""
        self.active_resolvers.pop(job_name)

    def start_download(self, job_name: str, file_name: str) -> (bool, str):
        """Start downloading the given file
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :return:
            A tuple containing a boolean indicating whether the download was started successfully
            and a string containing the status of the file or the error message if download
            could not be started"""
        job = self.jobs[job_name]
        if self.download_queues.get(job_name) is None:
            self.__setup_downloader(job_name)

        self.download_queues[job_name].download_file(job.get_file_by_name(file_name))

        file = job.get_file_by_name(file_name)
        if (
            file.status == FileModel.STATUS_DOWNLOADING
            or file.status == FileModel.STATUS_QUEUED
        ):
            return False, "File is already downloading or queued."
        file.status = FileModel.STATUS_QUEUED
        get_file_model_dao().update_file_model_status(file.id, file.status)
        return True, FileModel.STATUS_QUEUED

    def stop_download(
        self, job_name: str, file_name: str, completion_event=None
    ) -> (bool, str):
        """Stop downloading the given file
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :return:
            A tuple containing a boolean indicating whether the download was stopped successfully
            and a string containing the status of the file or the error message if download
            could not be stopped"""
        if job_name not in self.download_queues:
            return False, f"Unknown job: {job_name}"
        if file_name not in self.download_queues[job_name].signals:
            return False, f"Unknown file: {file_name} in job {job_name}"

        if completion_event is not None:
            self.download_queues[job_name].register_listener(
                completion_event, file_name, FileModel.STATUS_STOPPED
            )
        self.download_queues[job_name].signals[file_name].cancel()
        return True, "Stopped"

    def __setup_downloader(self, job_name: str) -> None:
        """Setup the downloader for the given job"""
        job = self.jobs[job_name]
        download_monitor = MainWindowJobMonitor(self, self.main_window, job_name)
        self.download_monitors[job_name] = download_monitor
        self.monitor_daemon.add_job_monitor(job_name, download_monitor)
        downloader = QueuedDownloader(job=job, monitor=self.monitor_daemon)
        self.download_queues[job_name] = downloader
        downloader.start()
