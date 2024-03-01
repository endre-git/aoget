import os
import logging
import time
from threading import Event
from typing import List
from db.aogetdb import get_job_dao
from config.app_config import get_config_value, AppConfig
from model.dto.job_dto import JobDTO
from model.file_model import FileModel
import model.yaml.job_yaml as job_yaml
from controller.job_task_controller import JobTaskController
from controller.app_state_handlers import AppStateHandlers

logger = logging.getLogger(__name__)


class JobController:
    """Controller for the main window jobs table and surrounding toolbar."""

    def __init__(
        self,
        app_state_handlers: AppStateHandlers,
        resume_callback: any,
        message_callback: any,
        background_controller: JobTaskController = None,
    ):
        self.app = app_state_handlers
        self.job_resumed_signal = resume_callback
        self.message_callback = message_callback
        if background_controller is None:
            self.background_controller = JobTaskController(self.app)
        else:
            self.background_controller = background_controller

    def set_file_controller(self, file_controller) -> None:
        """Set the file controller"""
        self.files = file_controller

    def get_job_dtos(self) -> List[JobDTO]:
        """Get all jobs as DTOs by mapping each to a DTO and returning the list"""
        job_dtos = []
        with self.app.db_lock:
            jobs = get_job_dao().get_all_jobs()
            job_dtos = list(map(lambda job: JobDTO.from_model(job), jobs))
        job_dtos.sort(key=lambda job: job.name)
        return job_dtos

    def get_job_dto_by_name(self, name) -> JobDTO:
        """Get a job DTO by its name"""
        with self.app.db_lock:
            job = get_job_dao().get_job_by_name(name)
            return JobDTO.from_model(job)

    def job_post_select(self, job_name: str, is_new=False) -> None:
        """Called after a job has been selected"""
        self.background_controller.resolve_file_sizes(job_name)
        if is_new and get_config_value(AppConfig.AUTO_START_JOBS):
            self.start_job(job_name)

    def resume_all_jobs(self) -> None:
        """Resume all jobs"""
        for job_dto in self.get_job_dtos():
            self.start_job(job_dto.name)

    def stop_all_jobs(self) -> None:
        """Pause all jobs"""
        for job_dto in self.get_job_dtos():
            self.stop_job(job_dto.name)

    def add_job(self, job) -> None:
        """Add a job"""
        with self.app.db_lock:
            get_job_dao().add_job(job)
            self.background_controller.resolve_file_sizes(job.name)

    def start_job(self, job_name: str) -> None:
        """Start the given job"""
        for file_dto in self.files.get_selected_file_dtos(job_name).values():
            self.files.start_download_file_dto(job_name, file_dto)

    def stop_job(self, job_name: str) -> None:
        """Stop the given job"""
        if self.app.downloads.is_running_for_job(job_name):
            for file_dto in self.files.get_selected_file_dtos(job_name).values():
                self.files.stop_download_file_dto(job_name, file_dto)

    def add_thread(self, job_name: str) -> None:
        """Increase the threads for the given job"""
        downloader = self.app.downloads.get_downloader(job_name)
        downloader.add_thread()
        self.app.update_cycle.journal_of_job(job_name).update_job_threads(
            threads_allocated=downloader.worker_pool_size,
            threads_active=downloader.get_active_thread_count(),
        )

    def remove_thread(self, job_name: str) -> None:
        """Decrease the threads for the given job"""
        downloader = self.app.downloads.get_downloader(job_name)
        if downloader.worker_pool_size == 1:
            return
        victim_file = None
        stopped = Event()
        if downloader.get_active_thread_count() == downloader.worker_pool_size:
            # find the active download with the lowest prio
            files = []
            for file_name in downloader.files_downloading:
                file_dto = self.files.get_selected_file_dtos(job_name)[file_name]
                files.append(file_dto)
            if len(files) > 0:
                victim_file = max(files, key=lambda file: file.priority)
                logger.info(
                    f"Stopping {victim_file.name} for {job_name} to reduce thread count."
                )
                self.files.stop_download(
                    job_name, victim_file.name, completion_event=stopped
                )
            else:
                logger.error(
                    f"""Could not find a file to stop for {job_name} to reduce thread
                    count (still reduced)"""
                )
        downloader.remove_thread()
        if victim_file is not None:
            stopped.wait(2)
            self.files.start_download(job_name, victim_file.name)  # re-queue the file
        self.app.update_cycle.journal_of_job(job_name).update_job_threads(
            threads_allocated=downloader.worker_pool_size,
            threads_active=downloader.get_active_thread_count(),
        )

    def delete_job(self, job_name: str, delete_from_disk=False) -> list:
        """Delete the given job
        :param job_name:
            The name of the job
        :param delete_from_disk:
            Whether to delete the files from disk"""
        messages = []
        t0 = time.time()
        self.app.downloads.kill_for_job(job_name)
        logger.info("Stopping downloader took %s seconds.", time.time() - t0)
        t0 = time.time()

        if delete_from_disk:
            target_folder = self.get_job_dto_by_name(job_name).target_folder
            # TODO file controller should delete files, not job controller
            for file in self.files.get_selected_file_dtos(job_name).values():
                try:
                    file_path = os.path.join(target_folder, file.name)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info("Deleted file from disk: %s", file_path)
                    elif (
                        file.status == FileModel.STATUS_COMPLETED
                        or file.status == FileModel.STATUS_STOPPED
                    ):
                        logger.error("File was not on disk: %s", file_path)
                except Exception as e:
                    messages.append(f"Could not delete file from disk: {e}")
                    logger.error("Could not delete file from disk: %s", e)
        logger.info("Deleting files from disk took %s seconds.", time.time() - t0)

        with self.app.db_lock:
            t0 = time.time()
            self.app.update_cycle.drop_job(job_name)
            self.app.cache.drop_job(job_name)
            self.app.journal_daemon.drop_job(job_name)
            logger.info(
                "Deleting journal and file cache took %s seconds.", time.time() - t0
            )
            t0 = time.time()
            get_job_dao().delete_job_by_name(job_name)
        logger.info("Deleting job from db took %s seconds.", time.time() - t0)
        return messages if len(messages) > 0 else None

    def export_job(self, job_name: str, target_file: str) -> None:
        """Export the given job to the given folder"""
        with self.app.db_lock:
            job = get_job_dao().get_job_by_name(job_name)
            job_yaml.write_job_yaml(job, target_file)
        logger.info("Exporting job %s to %s", job_name, target_file)

    def import_job(self, source_file: str) -> tuple[JobDTO, list]:
        """Import a job from the given file
        :param source_file:
            The source file
        :return:
            A tuple of the imported job and a list of files that were imported with it
        """
        return job_yaml.read_from_yaml(source_file)

    def health_check(self, job_name: str) -> None:
        """Perform a health check"""
        self.app.downloads.get_downloader(job_name).health_check(
            self.files.get_selected_file_dtos(job_name).values(), self.message_callback
        )

    def validate_file_states(self) -> None:
        """Validate the file states after application start.
        This is done on separate threads for each job."""
        files_per_job = self.app.cache.get_cache()
        for job_name, files in files_per_job.items():
            self.app.downloads.get_downloader(job_name).resume_files(
                files=files,
                file_controller=self.files,
                callback=self.job_resumed_signal,
            )

    def create_job_from_dto(self, job_dto: JobDTO) -> int:
        """Add a job from a DTO"""
        with self.app.db_lock:
            job = get_job_dao().create_job(
                job_dto.name, job_dto.page_url, job_dto.target_folder, commit=False
            )
            job_dto.merge_into_model(job)
            get_job_dao().save_job(job)
            return job.id

    def update_job_from_dto(self, job_dto: JobDTO) -> None:
        """Update a job from a DTO"""
        with self.app.db_lock:
            job = get_job_dao().get_job_by_name(job_dto.name)
            job_dto.merge_into_model(job)
            get_job_dao().save_job(job)

    def is_job_downloading(self, job_name: str) -> bool:
        """Check if the given job had active downloads."""
        return self.app.downloads.is_job_downloading(job_name)

    def job_exists(self, job_name: str) -> bool:
        """Check if a job exists"""
        with self.app.db_lock:
            return get_job_dao().get_job_by_name(job_name) is not None
