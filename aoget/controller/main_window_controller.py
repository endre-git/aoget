import time
import logging
from typing import Any
import threading
from db.aogetdb import get_job_dao, get_file_model_dao
from model.job import Job
from util.aogetutil import get_crash_report
from config.app_config import get_config_value, AppConfig
from controller.app_state_handlers import AppStateHandlers
from controller.job_controller import JobController
from controller.file_model_controller import FileModelController

logger = logging.getLogger(__name__)


class MainWindowController:
    """Controller class for the main window. Implements data binds beetween the UI and the
    underlying models."""

    def __init__(self, main_window: Any, aoget_db: Any):
        self.main_window = main_window
        self.db_lock = aoget_db.state_lock
        app_state_handlers = AppStateHandlers(self.db_lock, self.main_window)
        self.handlers = app_state_handlers
        self.validation_is_running = False

        self.jobs = JobController(
            app_state_handlers=app_state_handlers,
            resume_callback=self.main_window.job_resumed_signal,
            message_callback=self.main_window.message_signal,
        )
        self.files = FileModelController(app_state_handlers=app_state_handlers)
        self.update_cycle = app_state_handlers.update_cycle
        self.cache = app_state_handlers.cache
        self.jobs.set_file_controller(self.files)

    def resume_state(self) -> None:

        # if had a crash, show the dialog
        crash_report = get_crash_report(get_config_value(AppConfig.CRASH_LOG_FILE_PATH))
        if crash_report:
            self.main_window.show_crash_report(crash_report)

        files_per_job = {}
        size_resolvers_to_start_for_jobs = []
        with self.db_lock:
            t0 = time.time()
            jobs = get_job_dao().get_all_jobs()
            logger.info("Loading jobs from db took %s seconds.", time.time() - t0)
            t0 = time.time()
            for job in jobs:
                # get the selected file dtos for each job and put them in files_per_job
                files_per_job[job.name] = self.files.get_selected_file_dtos(
                    job_id=job.id
                )

                # validate the cache fields in the job object
                job.selected_files_with_known_size = len(
                    list(
                        filter(
                            lambda file: file.size_bytes is not None
                            and file.size_bytes > -1,
                            files_per_job[job.name].values(),
                        )
                    )
                )
                job.selected_files_count = len(files_per_job[job.name])
                job.downloaded_bytes = (
                    get_file_model_dao().get_total_downloaded_bytes_for_job(job.id)
                ) or 0
                if job.downloaded_bytes == job.total_size_bytes:
                    job.status = Job.STATUS_COMPLETED
                get_job_dao().save_job(job)
                if (
                    job.selected_files_count > 0
                    and job.selected_files_with_known_size < job.selected_files_count
                ):
                    size_resolvers_to_start_for_jobs.append(job.name)
        logger.info("Cache buildup took %s seconds.", time.time() - t0)
        t0 = time.time()

        # create a journal for each job
        for job_name in files_per_job.keys():
            self.update_cycle.create_journal(job_name)
        self.cache.set_cache(files_per_job)
        logger.info("Journal creation took %s seconds.", time.time() - t0)
        t0 = time.time()

        self.validation_thread = threading.Thread(
            target=self.jobs.validate_file_states, name="File state validation"
        )
        self.validation_is_running = True
        self.validation_thread.start()

        # start size resolvers where applicable
        for job_name in size_resolvers_to_start_for_jobs:
            self.jobs.start_size_resolver_for_job(job_name)

    def set_global_bandwidth_limit(self, rate_limit_bps: int) -> None:
        """Set the global bandwidth limit"""
        self.handlers.rate_limiter.set_global_rate_limit(rate_limit_bps)

    def actualize_config(self) -> None:
        """Apply the configuration as it is in the current state of AppConfig"""
        self.handlers.downloads.set_retry_attempts(
            get_config_value(AppConfig.DOWNLOAD_RETRY_ATTEMPTS)
        )

    def on_resolver_finished(self, job_name: str) -> None:
        """Called when a resolver has finished"""
        self.active_resolvers.pop(job_name)

    def stop_all_jobs(self) -> None:
        """Stop all jobs"""
        self.jobs.stop_all_jobs()

    def resume_all_jobs(self) -> None:
        """Resume all jobs"""
        self.jobs.resume_all_jobs()

    def shutdown(self) -> None:
        """Shutdown the controller"""
        self.handlers.downloads.shutdown_all()
