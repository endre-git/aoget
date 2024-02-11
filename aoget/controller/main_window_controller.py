import os
import time
import logging
from typing import Any
import threading
from threading import Event
from controller.journal_daemon import JournalDaemon
from web.queued_downloader import QueuedDownloader
from db.aogetdb import get_job_dao, get_file_model_dao, get_file_event_dao
from model.file_model import FileModel
from model.job import Job
import model.yaml.job_yaml as job_yaml
from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO
from model.dto.file_event_dto import FileEventDTO
from model.job_updates import JobUpdates
from util.disk_util import get_all_file_names_from_folders
from util.aogetutil import get_crash_report
from config.app_config import get_config_value, AppConfig
from controller.derived_field_calculator import DerivedFieldCalculator
from web.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class MainWindowController:
    """Controller class for the main window. Implements data binds beetween the UI and the
    underlying models."""

    FILE_DELETION_WAIT_SECONDS = 5

    def __init__(self, main_window: Any, aoget_db: Any):
        self.main_window = main_window
        self.journal_daemon = JournalDaemon(
            update_interval_seconds=1, journal_processor=self
        )
        self.db_lock = aoget_db.state_lock
        self.journal = {}
        self.job_downloaders = {}
        self.file_dto_cache = {}
        self.rate_limiter = RateLimiter()
        self.validation_is_running = False

    def resume_state(self) -> None:

        # if had a crash, show the dialog
        crash_report = get_crash_report(get_config_value(AppConfig.CRASH_LOG_FILE_PATH))
        if crash_report:
            self.main_window.show_crash_report(crash_report)

        files_per_job = {}
        with self.db_lock:
            t0 = time.time()
            jobs = get_job_dao().get_all_jobs()
            logger.info("Loading jobs from db took %s seconds.", time.time() - t0)
            t0 = time.time()
            for job in jobs:
                # get the selected file dtos for each job and put them in files_per_job
                files_per_job[job.name] = self.get_selected_file_dtos(job_id=job.id)

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
        logger.info("Cache buildup took %s seconds.", time.time() - t0)
        t0 = time.time()

        # create a journal for each job
        for job_name in files_per_job.keys():
            self.journal[job_name] = JobUpdates(job_name)
        self.file_dto_cache = files_per_job
        logger.info("Journal creation took %s seconds.", time.time() - t0)
        t0 = time.time()

        self.validation_thread = threading.Thread(
            target=self.__validate_file_states, name="File state validation"
        )
        self.validation_is_running = True
        self.validation_thread.start()

    def set_global_bandwidth_limit(self, rate_limit_bps: int) -> None:
        """Set the global bandwidth limit"""
        self.rate_limiter.set_global_rate_limit(rate_limit_bps)

    def get_job_dtos(self) -> list:
        """Get all jobs as DTOs by mapping each to a DTO and returning the list"""
        job_dtos = []
        with self.db_lock:
            jobs = get_job_dao().get_all_jobs()
            job_dtos = list(map(lambda job: JobDTO.from_model(job), jobs))
        # sort by job name
        job_dtos.sort(key=lambda job: job.name)
        # create a journal entry for each job
        return job_dtos

    def get_largest_fileset_length(self) -> int:
        """Get the length of the largest fileset"""
        return max(map(lambda fileset: len(fileset), self.file_dto_cache.values()))

    def get_selected_file_dtos(self, job_name: str = None, job_id: int = -1) -> dict:
        """Get all selected files as DTOs by mapping each to a DTO and returning the list"""
        if job_name is None and job_id == -1:
            raise ValueError("Either job_name or job_id must be set.")

        if job_name in self.file_dto_cache:
            return self.file_dto_cache[job_name]

        with self.db_lock:
            t0 = time.time()
            if job_id == -1:
                job_id = get_job_dao().get_job_by_name(job_name).id
            else:
                job_name = get_job_dao().get_job_by_id(job_id).name
            file_models = get_file_model_dao().get_selected_files_of_job(
                job_id, eager_event_loading=True
            )
            logger.info(
                "Loading files of job %s from db took %s seconds.",
                job_name,
                time.time() - t0,
            )
            t0 = time.time()
            file_dtos = dict(
                map(
                    lambda file: (file.name, FileModelDTO.from_model(file, job_name)),
                    file_models,
                )
            )
            self.file_dto_cache[job_name] = file_dtos
            logger.info(
                "Mapping files of job %s to DTOs took %s seconds.",
                job_name,
                time.time() - t0,
            )
            return file_dtos

    def get_file_event_dtos(self, job_name: str, file_name: str) -> list:
        """Get all file events as DTOs by mapping each to a DTO and returning the list"""
        with self.db_lock:
            job_id = get_job_dao().get_job_by_name(job_name).id
            file_id = get_file_model_dao().get_file_model_by_name(job_id, file_name).id
            file_events = get_file_event_dao().get_file_events_by_file_id(file_id)
            file_event_dtos = list(
                map(lambda event: FileEventDTO.from_model(event), file_events)
            )
            # sort by timestamp
            file_event_dtos.sort(key=lambda event: event.timestamp)
            return file_event_dtos

    def get_job_dto_by_name(self, name) -> JobDTO:
        """Get a job DTO by its name"""
        with self.db_lock:
            job = get_job_dao().get_job_by_name(name)
            return JobDTO.from_model(job)

    def get_file_dto(self, job_name, file_name) -> FileModelDTO:
        """Get a file DTO by its name"""
        with self.db_lock:
            job_id = get_job_dao().get_job_by_name(job_name).id
            file_model = get_file_model_dao().get_file_model_by_name(job_id, file_name)
            return FileModelDTO.from_model(file_model, job_name)

    # direct DB link, won't work from cache, won't update cache
    def get_file_dtos_by_job_id(self, job_id: int) -> list:
        """Get all file DTOs by job id"""
        with self.db_lock:
            job_name = get_job_dao().get_job_by_id(job_id).name
            file_models = get_file_model_dao().get_files_by_job_id(job_id)
            file_dtos = list(
                map(
                    lambda file: FileModelDTO.from_model(file, job_name=job_name),
                    file_models,
                )
            )
            return file_dtos

    def job_post_select(self, job_name: str, is_new=False) -> None:
        """Called after a job has been selected"""
        self.__resolve_file_sizes(job_name)
        if is_new and get_config_value(AppConfig.AUTO_START_JOBS):
            self.start_job(job_name)

    def add_job(self, job) -> None:
        """Add a job"""
        with self.db_lock:
            get_job_dao().add_job(job)
            self.__resolve_file_sizes(job.name)

    def resolve_file_url(self, job_name: str, file_name: str) -> str:
        """Resolve the URL of a file"""
        return self.get_selected_file_dtos(job_name)[file_name].url

    def resolve_local_file_path(self, job_name: str, file_name: str) -> str:
        """Resolve the local file path of a file"""
        with self.db_lock:
            job = get_job_dao().get_job_by_name(job_name)
            if job is None:
                raise ValueError("Unknown job: " + job_name)
            file = get_file_model_dao().get_file_model_by_name(job.id, file_name)
            if file is None:
                raise ValueError("Unknown file: " + file_name)
            return file.get_target_path()

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
        if self.job_downloaders.get(job_name) is None:
            return self.start_download(job_name, file_name)
        if file_name in self.job_downloaders[job_name].files_in_queue:
            return True, FileModel.STATUS_QUEUED
        if file_name in self.job_downloaders[job_name].files_downloading:
            stopped_event = Event()
            # stop the current download and wait for it to conclude
            could_stop, msg = self.stop_download(job_name, file_name, stopped_event)
            if not could_stop:
                return False, msg
            stopped_event.wait(self.FILE_DELETION_WAIT_SECONDS)
        # delete file from disk
        try:
            file_path = self.resolve_local_file_path(job_name, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
            # reset downloaded bytes
            self.__journal_of_job(job_name).update_file_download_progress(
                file_name, 0, -1
            )
        except Exception as e:
            logger.error("Could not delete file from disk: %s", e)
            return False, "Could not delete file from disk."
        return self.start_download(job_name, file_name)

    def __is_size_resolver_running(self, job_name: str) -> bool:
        """Check if the size resolver is running for the given job"""
        return (
            job_name in self.job_downloaders
            and self.job_downloaders[job_name].is_resolving_file_sizes()
        )

    def __resolve_file_sizes(self, job_name: str) -> None:
        """Resolve the file sizes of all selected files that have an unknown size"""
        if self.__is_size_resolver_running(job_name):
            return
        files_with_unknown_size = []
        with self.db_lock:
            job = get_job_dao().get_job_by_name(job_name)
            if job.selected_files_count == job.selected_files_with_known_size:
                return
            job_id = job.id
            file_models_with_unknown_size = []
            if job_name in self.file_dto_cache.keys():
                files_with_unknown_size = list(
                    filter(
                        lambda file: file.size_bytes is None or file.size_bytes == -1,
                        self.file_dto_cache[job_name].values(),
                    )
                )
            else:
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
            self.__setup_downloader(job_name)
            self.job_downloaders[job_name].resolve_file_sizes(
                job_name, files_with_unknown_size
            )

    def __validate_file_states(self) -> None:
        """Validate the file states after application start.
        This is done on separate threads for each job."""
        files_per_job = self.file_dto_cache
        for job_name, files in files_per_job.items():
            self.__setup_downloader(job_name)
            self.job_downloaders[job_name].resume_files(
                files=files,
                file_controller=self,
                callback=self.main_window.job_resumed_signal,
            )

    def on_resolver_finished(self, job_name: str) -> None:
        """Called when a resolver has finished"""
        self.active_resolvers.pop(job_name)

    def create_job_from_dto(self, job_dto: JobDTO) -> int:
        """Add a job from a DTO"""
        with self.db_lock:
            job = get_job_dao().create_job(
                job_dto.name, job_dto.page_url, job_dto.target_folder, commit=False
            )
            job_dto.merge_into_model(job)
            get_job_dao().save_job(job)
            return job.id

    def update_job_from_dto(self, job_dto: JobDTO) -> None:
        """Update a job from a DTO"""
        with self.db_lock:
            job = get_job_dao().get_job_by_name(job_dto.name)
            job_dto.merge_into_model(job)
            get_job_dao().save_job(job)

    def add_files_to_job(self, job_id: int, file_dtos: list) -> None:
        """Add files to a job"""
        with self.db_lock:
            job = get_job_dao().get_job_by_id(job_id)
            selected_count = 0
            known_size_count = 0
            for file_dto in file_dtos:
                file_model = get_file_model_dao().create_file_model(
                    url=file_dto.url, job=job, commit=False
                )
                if file_dto.selected:
                    selected_count += 1
                if file_dto.size_bytes is not None and file_dto.size_bytes > -1:
                    known_size_count += 1
                file_dto.merge_into_model(file_model)
                job.add_file(file_model)
            job.selected_files_count = selected_count
            job.selected_files_with_known_size = known_size_count
            get_job_dao().save_job(job)

            selected_file_list = list(filter(lambda file: file.selected, file_dtos))
            selected_files = dict(
                map(lambda file: (file.name, file), selected_file_list)
            )
            self.file_dto_cache[job.name] = selected_files

    def update_selected_files(self, job_id: int, file_dtos_by_name: dict) -> None:
        """Update selected files"""
        with self.db_lock:
            job = get_job_dao().get_job_by_id(job_id)
            for file in job.files:
                file_dto = file_dtos_by_name[file.name]
                if file_dto is not None:
                    file.selected = file_dto.selected
                else:
                    file.selected = False
            selected_file_list = list(
                filter(lambda file: file.selected, file_dtos_by_name.values())
            )
            selected_files = dict(
                map(lambda file: (file.name, file), selected_file_list)
            )
            job.selected_files_count = len(selected_files)
            self.file_dto_cache[job.name] = selected_files

            get_job_dao().save_job(job)

    def health_check(self, job_name: str, callback: any) -> None:
        """Perform a health check"""
        if job_name not in self.job_downloaders:
            self.__setup_downloader(job_name)
        self.job_downloaders[job_name].health_check(
            self.get_selected_file_dtos(job_name).values(), callback
        )

    def start_download(self, job_name: str, file_name: str) -> tuple[bool, str]:
        """Start downloading the given file
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :return:
            A tuple containing a boolean indicating whether the download was started successfully
            and a string containing the status of the file or the error message if download
            could not be started"""
        if job_name not in self.job_downloaders:
            self.__setup_downloader(job_name)

        queue = self.job_downloaders[job_name]
        if file_name in queue.files_in_queue:
            return False, "File is already in queue."
        if file_name in queue.files_downloading:
            return False, "File is already downloading."
        file_dto = self.get_file_dto(job_name, file_name)
        self.job_downloaders[job_name].download_file(file_dto)
        return True, FileModel.STATUS_QUEUED

    def stop_download(
        self, job_name: str, file_name: str, completion_event=None, add_to_journal=True
    ) -> tuple[bool, str]:
        """Stop downloading the given file
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :return:
            A tuple containing a boolean indicating whether the download was stopped successfully
            and a string containing the status of the file or the error message if download
            could not be stopped"""
        if job_name not in self.job_downloaders:
            return False, f"Unknown job: {job_name}"
        if file_name not in self.job_downloaders[job_name].signals:
            # download didn't start yet
            self.job_downloaders[job_name].cancel_download(file_name)
            if add_to_journal:
                self.__journal_of_job(job_name).update_file_status(
                    file_name=file_name, status=FileModel.STATUS_STOPPED
                )
            return True, FileModel.STATUS_STOPPED

        if completion_event is not None:
            self.job_downloaders[job_name].register_listener(
                completion_event, file_name, FileModel.STATUS_STOPPED
            )
        self.job_downloaders[job_name].signals[file_name].cancel()
        if add_to_journal:
            self.__journal_of_job(job_name).update_file_status(
                file_name=file_name, status=FileModel.STATUS_STOPPING
            )
        return True, FileModel.STATUS_STOPPING

    def start_job(self, job_name: str) -> None:
        """Start the given job"""
        self.__setup_downloader(job_name)
        for file_dto in self.get_selected_file_dtos(job_name).values():
            if file_dto.status not in [
                FileModel.STATUS_DOWNLOADING,
                FileModel.STATUS_COMPLETED,
                FileModel.STATUS_QUEUED,
            ]:
                self.job_downloaders[job_name].download_file(file_dto)
                self.__journal_of_job(job_name).update_file_status(
                    file_name=file_dto.name, status=FileModel.STATUS_QUEUED
                )

    def resume_all_jobs(self) -> None:
        """Resume all jobs"""
        for job_dto in self.get_job_dtos():
            self.start_job(job_dto.name)

    def start_downloads(self, job_name: str, file_names: list) -> None:
        """Start the given downloads for multiple files"""
        self.__setup_downloader(job_name)
        relevant_file_dtos = list(
            filter(
                lambda file: file.name in file_names,
                self.get_selected_file_dtos(job_name).values(),
            )
        )
        for file_dto in relevant_file_dtos:
            if file_dto.status not in [
                FileModel.STATUS_DOWNLOADING,
                FileModel.STATUS_COMPLETED,
                FileModel.STATUS_QUEUED,
            ]:
                self.job_downloaders[job_name].download_file(file_dto)
                self.__journal_of_job(job_name).update_file_status(
                    file_name=file_dto.name, status=FileModel.STATUS_QUEUED
                )

    def stop_downloads(self, job_name: str, file_names: list) -> None:
        """Stop the given downloads for multiple files"""
        relevant_file_dtos = list(
            filter(
                lambda file: file.name in file_names,
                self.get_selected_file_dtos(job_name).values(),
            )
        )
        if job_name in self.job_downloaders:
            for file_dto in relevant_file_dtos:
                if file_dto.status == FileModel.STATUS_DOWNLOADING:
                    self.stop_download(job_name, file_dto.name, add_to_journal=False)
                elif file_dto.status == FileModel.STATUS_QUEUED:
                    self.stop_download(job_name, file_dto.name, add_to_journal=True)

    def stop_job(self, job_name: str) -> None:
        """Stop the given job"""
        if job_name in self.job_downloaders:
            for file_dto in self.get_selected_file_dtos(job_name).values():
                if file_dto.status == FileModel.STATUS_DOWNLOADING:
                    self.stop_download(job_name, file_dto.name, add_to_journal=False)
                elif file_dto.status == FileModel.STATUS_QUEUED:
                    self.stop_download(job_name, file_dto.name, add_to_journal=True)

    def stop_all_jobs(self) -> None:
        """Stop all jobs"""
        for job_name in self.job_downloaders.keys():
            self.stop_job(job_name)

    def remove_files_from_job(
        self, job_name: str, file_names: list, delete_from_disk: bool = False
    ) -> list:
        """Remove the given files from the given job
        :param job_name:
            The name of the job
        :param file_names:
            The names of the files
        :param delete_from_disk:
            Whether to delete the files from disk
        :return:
            A list of messages, empty if no errors occurred"""
        messages = []
        relevant_file_dtos = list(
            filter(
                lambda file: file.name in file_names,
                self.get_selected_file_dtos(job_name).values(),
            )
        )
        for file_dto in relevant_file_dtos:
            could_remove, msg = self.remove_file_from_job(
                job_name, file_dto.name, delete_from_disk
            )
            if not could_remove:
                messages.append(msg)
        return messages if len(messages) > 0 else None

    def delete_job(self, job_name: str, delete_from_disk=False) -> list:
        """Delete the given job
        :param job_name:
            The name of the job
        :param delete_from_disk:
            Whether to delete the files from disk"""
        messages = []
        t0 = time.time()
        if job_name in self.job_downloaders:
            self.job_downloaders[job_name].kill()
            self.job_downloaders.pop(job_name)
        logger.info("Stopping downloader took %s seconds.", time.time() - t0)
        t0 = time.time()

        if delete_from_disk:
            target_folder = self.get_job_dto_by_name(job_name).target_folder
            for file in self.get_selected_file_dtos(job_name).values():
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
        t0 = time.time()

        if job_name in self.journal:
            self.journal.pop(job_name)
        if job_name in self.file_dto_cache:
            self.file_dto_cache.pop(job_name)
        logger.info(
            "Deleting journal and file cache took %s seconds.", time.time() - t0
        )
        t0 = time.time()
        with self.db_lock:
            job = get_job_dao().get_job_by_name(job_name)
            get_job_dao().delete_job(job)
        logger.info("Deleting job from db took %s seconds.", time.time() - t0)
        return messages if len(messages) > 0 else None

    def export_job(self, job_name: str, target_file: str) -> None:
        """Export the given job to the given folder"""
        with self.db_lock:
            job = get_job_dao().get_job_by_name(job_name)
            job_yaml.write_job_yaml(job, target_file)
        logger.info("Exporting job %s to %s", job_name, target_file)

    def import_job(self, source_file: str) -> (JobDTO, list):
        """Import a job from the given file"""
        return job_yaml.read_from_yaml(source_file)

    def remove_file_from_job(
        self, job_name: str, file_name: str, delete_from_disk=False
    ) -> (bool, str):
        """Remove the given file from the given job
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :param delete_from_disk:
            Whether to delete the file from disk
        :return:
            A tuple containing a boolean indicating whether the file was removed successfully
            and a string containing the status of the file or the error message if removal
            could not be completed"""
        if (
            job_name in self.job_downloaders
            and file_name not in self.job_downloaders[job_name].signals
        ):
            # download not active, but might be queued already
            self.job_downloaders[job_name].cancel_download(file_name)
        elif (
            job_name in self.job_downloaders
            and file_name in self.job_downloaders[job_name].files_downloading
        ):
            stopped_event = Event()
            # stop the current download and wait for it to conclude
            could_stop, msg = self.stop_download(job_name, file_name, stopped_event)
            if not could_stop:
                return False, msg
            stopped_event.wait(self.FILE_DELETION_WAIT_SECONDS)
        # delete file from disk
        if delete_from_disk:
            try:
                file_path = self.resolve_local_file_path(job_name, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error("Could not delete file from disk: %s", e)
                return False, f"Could not delete {file_name} from disk."

        # set unselected
        self.__journal_of_job(job_name).deselect_file(file_name)
        return True, ""

    def __journal_of_job(self, job_name: str) -> JobUpdates:
        """Get the journal of a job.
        :param job_name:
            The name of the job
        :return:
            The job's journal"""
        if job_name not in self.journal:
            self.journal[job_name] = JobUpdates(job_name)
        return self.journal[job_name]

    def is_job_downloading(self, job_name: str) -> bool:
        """Check if the given job had active downloads."""
        return (
            job_name in self.job_downloaders
            and self.job_downloaders[job_name].is_downloading()
        )

    def job_exists(self, job_name: str) -> bool:
        """Check if a job exists"""
        with self.db_lock:
            return get_job_dao().get_job_by_name(job_name) is not None

    def shutdown(self) -> None:
        """Shutdown the controller"""
        for job_name in self.job_downloaders.keys():
            self.job_downloaders[job_name].kill()
        self.journal_daemon.stop()

    def all_files_in_job_folders(self) -> list:
        """Get all file names from all job folders"""
        job_folders = []
        with self.db_lock:
            jobs = get_job_dao().get_all_jobs()
            job_folders = list(map(lambda job: job.target_folder, jobs))
        if len(job_folders) > 0:
            return get_all_file_names_from_folders(job_folders)
        else:
            return []

    def all_files_in_jobs(self) -> list:
        """Get all file names from all job folders"""
        job_names = []
        all_file_names = []
        with self.db_lock:
            jobs = get_job_dao().get_all_jobs()
            job_names = list(map(lambda job: job.name, jobs))
        for job_name in job_names:
            # collect all files from selected_file_dtos
            file_dtos = self.get_selected_file_dtos(job_name)
            file_names = list(map(lambda file: file.name, file_dtos.values()))
            all_file_names.extend(file_names)
        return all_file_names

    def __setup_downloader(
        self,
        job_name: str,
    ) -> None:
        """Setup the downloader for the given job"""
        if job_name not in self.job_downloaders:
            job_dto = None
            with self.db_lock:
                job = get_job_dao().get_job_by_name(job_name)
                job_dto = JobDTO.from_model(job)
            if job_dto is None:
                raise ValueError("Unknown job: " + job_name)
            worker_pool_size = (
                job_dto.threads_allocated
                if job_dto.threads_allocated
                else get_config_value(AppConfig.PER_JOB_DEFAULT_THREAD_COUNT)
            )
            downloader = QueuedDownloader(
                job=job, monitor=self.journal_daemon, worker_pool_size=worker_pool_size
            )
            self.job_downloaders[job_name] = downloader
            downloader.start_download_threads()
            self.__journal_of_job(job_name).update_job_threads(
                threads_allocated=worker_pool_size,
                threads_active=downloader.get_active_thread_count(),
            )

    def __update_rate_limits(self) -> None:
        """Update the rate limits"""
        total_thread_count = 0
        for job in self.job_downloaders.keys():
            total_thread_count += self.job_downloaders[job].get_active_thread_count()
        if total_thread_count == 0:
            return
        per_thread_limit = self.rate_limiter.get_per_thread_limit(total_thread_count)
        for job in self.job_downloaders.keys():
            self.job_downloaders[job].set_rate_limit(per_thread_limit)

    def add_thread(self, job_name: str) -> None:
        """Increase the threads for the given job"""
        self.__setup_downloader(job_name)
        self.job_downloaders[job_name].add_thread()
        self.__journal_of_job(job_name).update_job_threads(
            threads_allocated=self.job_downloaders[job_name].worker_pool_size,
            threads_active=self.job_downloaders[job_name].get_active_thread_count()
        )

    def remove_thread(self, job_name: str) -> None:
        """Decrease the threads for the given job"""
        self.__setup_downloader(job_name)
        downloader = self.job_downloaders[job_name]
        victim_file = None
        stopped = Event()
        if downloader.get_active_thread_count() == downloader.worker_pool_size:
            # find the active download with the lowest prio
            files = []
            for file_name in downloader.files_downloading:
                file_dto = self.get_selected_file_dtos(job_name)[file_name]
                files.append(file_dto)
            if len(files) > 0:
                victim_file = max(files, key=lambda file: file.priority)
                logger.info(
                    f"Stopping {victim_file.name} for {job_name} to reduce thread count."
                )
                self.stop_download(job_name, victim_file.name, completion_event=stopped)
        self.job_downloaders[job_name].remove_thread()
        if victim_file is not None:
            stopped.wait(2)
            self.start_download(job_name, victim_file.name)  # re-queue the file
        self.__journal_of_job(job_name).update_job_threads(
            threads_allocated=self.job_downloaders[job_name].worker_pool_size,
            threads_active=self.job_downloaders[job_name].get_active_thread_count()
        )

    def increase_file_priorities(self, job_name: str, file_names: list) -> None:
        """Increase the priority of the given files"""
        for file_name in file_names:
            file = self.get_selected_file_dtos(job_name)[file_name]
            current_priority = file.priority
            if current_priority > 1:
                file.priority = file.priority - 1
                self.__journal_of_job(job_name).update_file_priority(
                    file_name, current_priority - 1
                )
                if job_name in self.job_downloaders:
                    self.job_downloaders[job_name].update_priority(file)

    def decrease_file_priorities(self, job_name: str, file_names: list) -> None:
        """Decrease the priority of the given files"""
        for file_name in file_names:
            file = self.get_selected_file_dtos(job_name)[file_name]
            current_priority = file.priority
            if current_priority < 3:
                file.priority = file.priority + 1
                self.__journal_of_job(job_name).update_file_priority(
                    file_name, current_priority + 1
                )
                if job_name in self.job_downloaders:
                    self.job_downloaders[job_name].update_priority(file)

    # TODO refactor this out of there. There should be a central update cycle handler
    def update_tick(self, journal: dict):
        """Called by the ticker to process the updates"""

        # join the keysets of the journal and the current job updates
        all_job_names = set(journal.keys()).union(set(self.journal.keys()))
        for jobname in all_job_names:
            if jobname in journal and jobname in self.journal:
                self.process_job_updates(journal[jobname], merge=True)
            elif jobname in self.journal:
                self.process_job_updates(self.journal[jobname], merge=False)
            else:
                self.process_job_updates(journal[jobname], merge=True)
        self.journal.clear()
        self.__update_rate_limits()

    # TODO refactor this out of here. There should be a central update cycle handler
    def process_job_updates(self, cycle_job_updates: JobUpdates, merge=True) -> None:
        """Process the cycle updates for a single job."""
        job_name = cycle_job_updates.job_name
        if merge:
            job_updates = self.journal[job_name] if job_name in self.journal else None
            if job_updates is None:
                job_updates = cycle_job_updates
            else:
                job_updates.merge(cycle_job_updates)
        else:
            job_updates = cycle_job_updates

        # filter file dtos that are not selected
        deselected_file_dtos = list(
            filter(
                lambda file: not file.selected,
                cycle_job_updates.file_model_updates.values(),
            )
        )
        if len(deselected_file_dtos) > 0:
            print('deselected_file_dtos: ' + str(deselected_file_dtos))

        derived_status = (
            Job.STATUS_RUNNING
            if self.is_job_downloading(job_name)
            else Job.STATUS_NOT_RUNNING
        )
        active_thread_count = (
            0
            if not self.is_job_downloading(job_name)
            else self.job_downloaders[job_name].get_active_thread_count()
        )
        allocated_thread_count = (
            0
            if not self.is_job_downloading(job_name)
            else self.job_downloaders[job_name].worker_pool_size
        )

        # update db
        with self.db_lock:
            # merge job updates into db
            job = get_job_dao().get_job_by_name(job_name)
            if job is None:
                logger.debug("Stale job update for: %s", job_name)
                return
            job.status = (
                derived_status if job.status is not Job.STATUS_COMPLETED else job.status
            )
            if job_updates.job_update is not None:
                job_updates.job_update.merge_into_model(job)
                job_updates.job_update.update_from_model(job)
            else:
                job_updates.job_update = JobDTO.from_model(job)

            job_updates.job_update.threads_active = active_thread_count
            job_updates.job_update.threads_allocated = allocated_thread_count
            # we increment the size with any size update that came in. It'd be more consistent if we
            # computed the size on the total fileset after each tick, but that'd be non-performant.
            job_size_bytes_increment = 0

            # merge file model updates into db
            for file_model_dto in job_updates.file_model_updates.values():
                job_id = get_job_dao().get_job_by_name(job_name).id
                file_model = get_file_model_dao().get_file_model_by_name(
                    job_id, file_model_dto.name
                )
                db_size = file_model.size_bytes if file_model else 0
                if (
                    file_model_dto.size_bytes is not None
                    and db_size != file_model_dto.size_bytes
                ):
                    job.selected_files_with_known_size += 1
                    job_size_bytes_increment += file_model_dto.size_bytes
                if file_model is None:
                    if file_model_dto.deleted:
                        logger.warn(
                            "Tried to delete an already deleted file model: %s",
                            file_model_dto.name,
                        )
                    else:
                        # TODO create and add the new model, and set it to file_model
                        logger.error("Branch not implemented")
                else:
                    file_model_dto.merge_into_model(file_model)

                if file_model is not None:
                    # back-populate DTO fields from DB for UI display
                    file_model_dto.update_from_model(file_model)

            for file_name, event_dtos in job_updates.file_event_updates.items():
                file_model_of_event = get_file_model_dao().get_file_model_by_name(
                    job.id, file_name
                )
                if file_model_of_event is None:
                    logger.error("File model not found for file event: %s", file_name)
                    continue
                for event_dto in event_dtos:
                    event = event_dto.build_model(file_model_of_event)
                    get_file_event_dao().add_file_event(event, commit=False)
                    if file_name in job_updates.file_model_updates:
                        job_updates.file_model_updates[file_name].last_event = (
                            event.event
                        )
                        job_updates.file_model_updates[
                            file_name
                        ].last_event_timestamp = event.timestamp
                if file_name not in job_updates.file_model_updates:
                    # backpopulate to update object for UI display
                    job_updates.file_model_updates[file_name] = FileModelDTO.from_model(
                        file_model_of_event, job_name
                    )

            # back-populate most recent file event to every file model DTO for UI display
            for file_model_dto in job_updates.file_model_updates.values():
                file_model = get_file_model_dao().get_file_model_by_name(
                    job.id, file_model_dto.name
                )
                if file_model is None:
                    logger.error(
                        "File model not found for file model DTO: %s",
                        file_model_dto.name,
                    )
                    continue
                file_model_dto.update_from_model(file_model)

                # sync up the local cache state
                if (
                    not file_model_dto.selected
                    and file_model_dto.name in self.file_dto_cache[job_name]
                ):
                    del self.file_dto_cache[job_name][file_model_dto.name]
                    DerivedFieldCalculator.file_deselected_in_job(
                        job_updates.job_update, file_model_dto
                    )
                    job_updates.job_update.merge_into_model(job)
                else:
                    self.file_dto_cache[job_name][file_model_dto.name] = file_model_dto

            # update the job-level size fields
            job.total_size_bytes += job_size_bytes_increment
            job_updates.job_update.total_size_bytes = job.total_size_bytes
            job_updates.job_update.selected_files_with_known_size = (
                job.selected_files_with_known_size
            )
            job_updates.job_update.selected_files_count = job.selected_files_count

            # downloaded bytes is a cache field, so we need to update it in the job object
            downloaded_bytes = (
                get_file_model_dao().get_total_downloaded_bytes_for_job(job.id) or 0
            )
            job.downloaded_bytes = downloaded_bytes
            job_updates.job_update.downloaded_bytes = downloaded_bytes
            if job.total_size_bytes == job.downloaded_bytes:
                job.status = Job.STATUS_COMPLETED
                job_updates.job_update.status = Job.STATUS_COMPLETED

            # downloaded files count
            completed_files = (
                get_file_model_dao().get_completed_file_count_for_job_id(job.id) or 0
            )
            job_updates.job_update.files_done = completed_files

            # commit db
            get_job_dao().save_job(job)

        # selectively update ui
        if job_updates.job_update is not None:
            if (
                job_name in self.job_downloaders
                and self.job_downloaders[job_name].is_resuming
            ):
                job_updates.job_update.status = "Resuming"
            self.main_window.update_job_signal.emit(job_updates.job_update)
        for file_model_dto in job_updates.file_model_updates.values():
            self.main_window.update_file_signal.emit(file_model_dto)
