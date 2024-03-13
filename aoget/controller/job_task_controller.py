import logging
from db.aogetdb import get_job_dao, get_file_model_dao
from model.dto.file_model_dto import FileModelDTO
from controller.app_state_handlers import AppStateHandlers

logger = logging.getLogger(__name__)


class JobTaskController:
    """Background task controller for job tasks."""

    def __init__(self, app_state_handlers: AppStateHandlers) -> None:
        self.db_lock = app_state_handlers.db_lock
        self.app = app_state_handlers

    # TODO app-cache
    def resolve_file_sizes(self, job_name: str) -> None:
        """Resolve the file sizes of all selected files that have an unknown size"""
        cache = self.app.cache
        if self.is_size_resolver_running(job_name):
            return
        files_with_unknown_size = []
        with self.db_lock:
            job = get_job_dao().get_job_by_name(job_name)
            if job.selected_files_count == job.selected_files_with_known_size:
                return
            job_id = job.id
            file_models_with_unknown_size = []
            if cache.is_cached_job(job_name):
                files_with_unknown_size = list(
                    filter(
                        lambda file: file.size_bytes is None or file.size_bytes == -1,
                        cache.get_files_of_job(job_name),
                    )
                )
            else:
                logger.warning(
                    "Job %s is not in cache, fetching files with unknown size from db.",
                    job_name,
                )
                file_models_with_unknown_size = (
                    get_file_model_dao().get_selected_files_with_unknown_size(job_id)
                )
                if len(file_models_with_unknown_size) > 0:
                    # map them to DTOs and add them to the list
                    files_with_unknown_size = list(
                        map(
                            lambda file: FileModelDTO.from_model(file, job_name),
                            file_models_with_unknown_size,
                        )
                    )
        if len(files_with_unknown_size) > 0:
            self.app.downloads.get_downloader(job_name).resolve_file_sizes(
                job_name, files_with_unknown_size
            )

    def is_size_resolver_running(self, job_name: str) -> bool:
        """Check if the size resolver is running for the given job"""
        downloads = self.app.downloads
        return (
            downloads.is_running_for_job(job_name)
            and downloads.get_downloader(job_name).is_resolving_file_sizes()
        )
