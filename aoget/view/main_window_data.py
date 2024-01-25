import logging
from typing import Any
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
                    if not file.validate_downloaded():
                        file.status = FileModel.STATUS_INVALID
                        file.add_event(
                            "Could not file local file despite marked as downloaded."
                        )
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
        if file.status == FileModel.STATUS_DOWNLOADING or file.status == FileModel.STATUS_QUEUED:
            return False, "File is already downloading or queued."
        file.status = FileModel.STATUS_QUEUED
        get_file_model_dao().update_file_model_status(file.id, file.status)
        return True, FileModel.STATUS_QUEUED

    def stop_download(self, job_name: str, file_name: str) -> (bool, str):
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
