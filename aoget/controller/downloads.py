from db.aogetdb import get_job_dao
from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO
from config.app_config import AppConfig, get_config_value
from web.queued_downloader import QueuedDownloader


class Downloads:
    """App-level downloads object that manages the downloaders for each job."""

    def __init__(
        self, app_state_handlers: any
    ):
        """Create a new Downloads object."""
        self.app = app_state_handlers
        self.job_downloaders = {}
        # can be disabled for testing
        self.start_download_threads = True

    def shutdown_for_job(self, job_name: str) -> None:
        """Kill the download of the given job if it exists."""
        if job_name in self.job_downloaders:
            self.job_downloaders[job_name].shutdown()
            self.job_downloaders.pop(job_name)

    def shutdown_all(self) -> None:
        """Kill all downloads."""
        for job_name in list(self.job_downloaders.keys()):
            self.shutdown_for_job(job_name)

    def is_running_for_job(self, job_name: str) -> bool:
        """Check if the download of the given job is running."""
        return job_name in self.job_downloaders.keys()

    def is_file_queued(self, job_name: str, file_name: str) -> bool:
        """Check if the given file is queued for download."""
        return (
            self.is_running_for_job(job_name)
            and file_name in self.job_downloaders[job_name].files_in_queue
        )

    def is_file_downloading(self, job_name: str, file_name: str) -> bool:
        """Check if the given file is downloading."""
        return (
            self.is_running_for_job(job_name)
            and file_name in self.job_downloaders[job_name].files_downloading
        )

    def get_downloader(
        self, job_name: str, create_if_not_exists: bool = True
    ) -> QueuedDownloader:
        """Get the downloader for the given job.
        :param job_name:
            The name of the job
        :param create_if_not_exists:
            Whether to create the downloader if it does not exist
        :return:
            The downloader"""
        if job_name not in self.job_downloaders and create_if_not_exists:
            self.__setup_downloader(job_name)
        return self.job_downloaders.get(job_name)

    def __setup_downloader(
        self,
        job_name: str,
    ) -> None:
        """Setup the downloader for the given job"""
        app = self.app
        if job_name not in self.job_downloaders:
            job_dto = None
            with app.db_lock:
                job = get_job_dao().get_job_by_name(job_name)
                job_dto = JobDTO.from_model(job)
            if job_dto is None:
                raise ValueError("Unknown job: " + job_name)
            worker_pool_size = (
                job_dto.threads_allocated
                if job_dto.threads_allocated
                else get_config_value(AppConfig.PER_JOB_DEFAULT_THREAD_COUNT)
            )
            retry_attempts = get_config_value(AppConfig.DOWNLOAD_RETRY_ATTEMPTS)
            downloader = QueuedDownloader(
                job=job_dto,
                journal_daemon=app.journal_daemon,
                worker_pool_size=worker_pool_size,
                download_retry_attempts=retry_attempts,
            )
            self.job_downloaders[job_name] = downloader
            if self.start_download_threads:
                downloader.start_download_threads()
            app.update_cycle.journal_of_job(job_name).update_job_threads(
                threads_allocated=worker_pool_size,
                threads_active=downloader.get_active_thread_count(),
            )

    def download_files(self, job_name: str, file_dtos: list) -> None:
        """Download the given files."""
        self.get_downloader(job_name).download_files(file_dtos)

    def dequeue_files(self, job_name: str, file_dtos: list) -> None:
        """Dequeue the given files."""
        self.get_downloader(job_name).dequeue_files(file_dtos)

    def stop_active_downloads(self, job_name: str, file_dtos: list) -> None:
        """Stop the active downloads for the given files."""
        self.get_downloader(job_name).stop_active_downloads(file_dtos)

    def download_file(self, job_name: str, file_dto: FileModelDTO) -> None:
        """Download the given file."""
        self.get_downloader(job_name).download_file(file_dto)

    def get_active_thread_count(self, job_name: str) -> int:
        """Get the active thread count for the given job."""
        if (
            not self.is_running_for_job(job_name)
            or not self.get_downloader(job_name).is_downloading()
        ):
            return 0
        return self.get_downloader(job_name).get_active_thread_count()

    def get_allocated_thread_count(self, job_name: str) -> int:
        """Get the allocated thread count for the given job."""
        if not self.is_running_for_job(job_name):
            with self.app.db_lock:
                job = get_job_dao().get_job_by_name(job_name)
                if job is None:
                    raise ValueError("Unknown job: " + job_name)
                if job.threads_allocated is None or job.threads_allocated < 1:
                    return get_config_value(AppConfig.PER_JOB_DEFAULT_THREAD_COUNT)
                return job.threads_allocated
        else:
            return self.get_downloader(job_name).worker_pool_size

    def is_job_resuming(self, job_name: str) -> bool:
        """Check if the given job is resuming."""
        return (
            self.is_running_for_job(job_name)
            and self.get_downloader(job_name).is_resuming
        )

    def is_job_downloading(self, job_name: str) -> bool:
        """Check if the given job is downloading."""
        return (
            self.is_running_for_job(job_name)
            and self.get_downloader(job_name).is_downloading()
        )

    def get_all_active_job_names(self) -> list:
        """Get all active job names"""
        return list(self.job_downloaders.keys())

    def set_retry_attempts(self, retry_attempts: int) -> None:
        """Set the retry attempts for all downloaders"""
        for downloader in self.job_downloaders.values():
            downloader.download_retry_attempts = retry_attempts
