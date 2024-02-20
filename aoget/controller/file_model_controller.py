import os
import time
import logging
from threading import Event
from db.aogetdb import get_job_dao, get_file_model_dao, get_file_event_dao
from model.file_model import FileModel
from model.dto.file_model_dto import FileModelDTO
from model.dto.file_event_dto import FileEventDTO
from util.disk_util import get_all_file_names_from_folders

logger = logging.getLogger(__name__)


class FileModelController:
    """Controller for file models"""

    FILE_DELETION_WAIT_SECONDS = 5

    def __init__(self, app_state_handlers):
        """Initialize the file model controller"""
        self.app = app_state_handlers
        self.db_lock = app_state_handlers.db_lock

    def get_selected_file_dtos(self, job_name: str = None, job_id: int = -1) -> dict:
        """Get all selected files as DTOs by mapping each to a DTO and returning the list"""
        app_cache = self.app.cache
        if job_name is None and job_id == -1:
            raise ValueError("Either job_name or job_id must be set.")

        if app_cache.is_cached_job(job_name):
            return app_cache.get_cached_files(job_name)

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
            app_cache.set_cached_files(job_name, file_dtos)
            logger.info(
                "Mapping files of job %s to DTOs took %s seconds.",
                job_name,
                time.time() - t0,
            )
            return file_dtos

    # TODO why is this not cached?
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

    def get_file_dto(self, job_name, file_name) -> FileModelDTO:
        """Get a file DTO by its name"""
        with self.db_lock:
            job_id = get_job_dao().get_job_by_name(job_name).id
            file_model = get_file_model_dao().get_file_model_by_name(job_id, file_name)
            return FileModelDTO.from_model(file_model, job_name)

    # direct DB link, doesn't load from cache, won't update cache
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

    def redownload_file(self, job_name: str, file_name: str) -> tuple[bool, str]:
        """Redownload the given file
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :return:
            A tuple containing a boolean indicating whether the download was started successfully
            and a string containing the status of the file or the error message if download
            could not be started"""
        if not self.app.downloads.is_running_for_job(job_name):
            return self.start_download(job_name, file_name)
        if self.app.downloads.is_file_queued(job_name, file_name):
            return True, FileModel.STATUS_QUEUED
        if self.app.downloads.is_file_downloading(job_name, file_name):
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
            self.app.update_cycle.journal_of_job(
                job_name
            ).update_file_download_progress(file_name, 0, -1)
        except Exception as e:
            logger.error("Could not delete file from disk: %s", e)
            return False, "Could not delete file from disk."
        return self.start_download(job_name, file_name)

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
            self.app.cache.set_cached_files(job.name, selected_files)

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
            self.app.cache.set_cached_files(job.name, selected_files)

            get_job_dao().save_job(job)

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
        if self.app.downloads.is_file_queued(job_name, file_name):
            return False, "File is already in queue."
        if self.app.downloads.is_file_downloading(job_name, file_name):
            return False, "File is already downloading."
        file_dto = self.get_file_dto(job_name, file_name)
        self.app.downloads.get_downloader(job_name).download_file(file_dto)
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
        if not self.app.downloads.is_running_for_job(job_name):
            return False, f"Unknown job: {job_name}"
        downloader = self.app.downloads.get_downloader(job_name)
        journal = self.app.update_cycle.journal_of_job(job_name)
        if file_name not in downloader.signals:
            # download didn't start yet
            downloader.cancel_download(file_name)
            if add_to_journal:
                journal.update_file_status(
                    file_name=file_name, status=FileModel.STATUS_STOPPED
                )
            return True, FileModel.STATUS_STOPPED

        if completion_event is not None:
            downloader.register_listener(
                completion_event, file_name, FileModel.STATUS_STOPPED
            )
        downloader.signals[file_name].cancel()
        if add_to_journal:
            journal.update_file_status(
                file_name=file_name, status=FileModel.STATUS_STOPPING
            )
        return True, FileModel.STATUS_STOPPING

    def start_downloads(self, job_name: str, file_names: list) -> None:
        """Start the given downloads for multiple files"""
        downloader = self.app.downloads.get_downloader(job_name)
        journal = self.app.update_cycle.journal_of_job(job_name)
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
                downloader.download_file(file_dto)
                journal.update_file_status(
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
        if self.app.downloads.is_running_for_job(job_name):
            for file_dto in relevant_file_dtos:
                if file_dto.status == FileModel.STATUS_DOWNLOADING:
                    self.stop_download(job_name, file_dto.name, add_to_journal=False)
                elif file_dto.status == FileModel.STATUS_QUEUED:
                    self.stop_download(job_name, file_dto.name, add_to_journal=True)

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

    def remove_file_from_job(
        self, job_name: str, file_name: str, delete_from_disk=False
    ) -> tuple[bool, str]:
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
        downloads = self.app.downloads
        journal = self.app.update_cycle.journal_of_job(job_name)
        if downloads.is_file_queued(job_name, file_name):
            # download not active, but might be queued already
            self.job_downloaders[job_name].cancel_download(file_name)
        elif downloads.is_file_downloading(job_name, file_name):
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
        journal.deselect_file(file_name)
        return True, ""

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

    def increase_file_priorities(self, job_name: str, file_names: list) -> None:
        """Increase the priority of the given files"""
        for file_name in file_names:
            file = self.get_selected_file_dtos(job_name)[file_name]
            current_priority = file.priority
            if current_priority > 1:
                file.priority = file.priority - 1
                journal = self.app.update_cycle.journal_of_job(job_name)
                journal.update_file_priority(file_name, current_priority - 1)
                if self.app.downloads.is_running_for_job(job_name):
                    downloader = self.app.downloads.get_downloader(job_name)
                    downloader.update_priority(file)

    def decrease_file_priorities(self, job_name: str, file_names: list) -> None:
        """Decrease the priority of the given files"""
        for file_name in file_names:
            file = self.get_selected_file_dtos(job_name)[file_name]
            current_priority = file.priority
            if current_priority < 3:
                file.priority = file.priority + 1
                journal = self.app.update_cycle.journal_of_job(job_name)
                journal.update_file_priority(file_name, current_priority + 1)
                if self.app.downloads.is_running_for_job(job_name):
                    downloader = self.app.downloads.get_downloader(job_name)
                    downloader.update_priority(file)

    def get_largest_fileset_length(self) -> int:
        """Get the length of the largest fileset"""
        return max(map(lambda fileset: len(fileset), self.app.cache.get_filesets()))
