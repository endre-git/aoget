import os
import logging
from typing import Any
from threading import Event
from .main_window_job_monitor import MainWindowJobMonitor
from aoget.web.journal_daemon import JournalDaemon
from web.queued_downloader import QueuedDownloader
from db.aogetdb import get_job_dao, get_file_model_dao, get_file_event_dao
from model.file_model import FileModel
from model.job import Job
from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO
from model.job_updates import JobUpdates
from util.disk_util import get_local_file_size

logger = logging.getLogger(__name__)


class MainWindowController:
    """Controller class for the main window. Implements data binds beetween the UI and the
    underlying models."""

    job_downloaders = {}
    download_monitors = {}
    scoped_session_factory = None
    journal = {}

    FILE_DELETION_WAIT_SECONDS = 5

    def __init__(self, main_window: Any, aoget_db: Any):
        self.main_window = main_window
        self.monitor_daemon = JournalDaemon(
            update_interval_seconds=1, journal_processor=self
        )
        self.aoget_db = aoget_db
        self.scoped_session_factory = aoget_db.scoped_session_factory
        self.db_lock = aoget_db.state_lock
        self.journal = {}

    def get_selected_filenames(self, job_name: str) -> list:
        """Get the names of all selected files"""
        return self.jobs[job_name].get_selected_filenames()

    def is_file_has_history(self, job_name: str, file_name: str) -> bool:
        """Check if the file has history"""
        return self.jobs[job_name].get_file_by_name(file_name).has_history()

    def resume_state(self) -> None:
        files_per_job = {}
        with self.db_lock:
            jobs = get_job_dao().get_all_jobs()
            for job in jobs:
                # get the selected file dtos for each job and put them in files_per_job
                files_per_job[job.name] = self.get_selected_file_dtos(job_id=job.id)

        # create a journal for each job
        for job_name in files_per_job.keys():
            self.journal[job_name] = JobUpdates(job_name)

        self.__validate_file_states(files_per_job=files_per_job)

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

    def get_selected_file_dtos(self, job_name: str = None, job_id: int = -1) -> list:
        """Get all selected files as DTOs by mapping each to a DTO and returning the list"""
        if job_name is None and job_id == -1:
            raise ValueError("Either job_name or job_id must be set.")
        if job_id == -1:
            job_id = get_job_dao().get_job_by_name(job_name).id
        file_models = get_file_model_dao().get_selected_files_of_job(job_id)
        file_dtos = list(
            map(lambda file: FileModelDTO.from_model(file, job_name), file_models)
        )
        # sort by file name
        file_dtos.sort(key=lambda file: file.name)
        return file_dtos

    def job_count(self) -> int:
        """Get the number of jobs"""
        return len(self.jobs)

    def get_job_by_name(self, name) -> Job:
        """Get a job by its name"""
        return self.jobs[name] or None

    def get_job_dto_by_name(self, name) -> JobDTO:
        """Get a job DTO by its name"""
        return JobDTO.from_model(self.jobs[name]) or None

    def get_file_dto(self, job_name, file_name) -> FileModelDTO:
        """Get a file DTO by its name"""
        with self.db_lock:
            job_id = get_job_dao().get_job_by_name(job_name).id
            file_model = get_file_model_dao().get_file_model_by_name(job_id, file_name)
            return FileModelDTO.from_model(file_model, job_name)

    def job_post_select(self, job_name: str) -> None:
        """Called after a job has been selected"""
        self.__resolve_file_sizes(job_name)

    def add_job(self, job) -> None:
        """Add a job"""
        get_job_dao().add_job(job)
        self.__resolve_file_sizes(job.name)

    def update_file_size(self, job_name, file_name, size):  # async
        """Update the size of a file"""
        # update app state
        for job_name in self.jobs.keys():
            for file in self.jobs[job_name].files:
                if file.name == file_name:
                    file.size_bytes = size
        # update journal
        self.job_updates[job_name].incremental_file_model_update(
            FileModelDTO(name=file_name, job_name=job_name, size_bytes=size)
        )
        # update ui
        self.main_window.resolved_file_size_signal.emit(job_name, file_name, size)

    def update_file_download_progress(
        self, job_name, file_name, downloaded_bytes, percent_completed, delta, eta
    ):  # async
        """Update the download progress of a file"""
        # update app state
        for job_name in self.jobs.keys():
            for file in self.jobs[job_name].files:
                if file.name == file_name:
                    file.downloaded_bytes = downloaded_bytes
        # update db
        self.job_updates[job_name].incremental_file_model_update(
            FileModelDTO(
                name=file_name, job_name=job_name, downloaded_bytes=downloaded_bytes
            )
        )
        # update ui
        self.main_window.update_file_progress_signal.emit(
            job_name, file_name, percent_completed, delta, eta
        )

    def update_file_status(self, job_name, file_name, status):
        """Update the status of a file.
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :param status:
            The new status of the file"""
        file = self.jobs[job_name].get_file_by_name(file_name)

        # update app state
        file.status = status
        # update db
        self.job_updates[job_name].incremental_file_model_update(
            FileModelDTO(name=file_name, job_name=job_name, status=status)
        )

        self.main_window.update_file_status_signal.emit(
            job_name,
            file_name,
            status,
            file.get_latest_history_timestamp(),
            file.get_latest_history_entry().event,
        )

    def resolve_file_url(self, job_name: str, file_name: str) -> str:
        """Resolve the URL of a file"""
        if job_name not in self.jobs:
            return ""
        return self.jobs[job_name].get_file_by_name(file_name).url

    def resolve_local_file_path(self, job_name: str, file_name: str) -> str:
        """Resolve the local file path of a file"""
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
            return True, "File is already downloading or queued."
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
            job_id = get_job_dao().get_job_by_name(job_name).id
            file_models = get_file_model_dao().get_selected_files_with_unknown_size(
                job_id
            )
            if len(file_models) > 0:
                # map them to DTOs and add them to the list
                files_with_unknown_size = list(
                    map(
                        lambda file: FileModelDTO.from_model(file, job_name),
                        file_models,
                    )
                )
        if len(files_with_unknown_size) > 0:
            self.__setup_downloader(
                job_name,
                start_downloads=False,
                files_with_unknown_size=files_with_unknown_size,
            )

    def __validate_file_states(self, files_per_job) -> None:
        """Validate the file states"""
        for job_name, files in files_per_job.items():
            for file in files:
                if file.status == FileModel.STATUS_DOWNLOADING:
                    logger.info(
                        "File %s was downloaded at last app run, will resume now.",
                        file.name,
                    )
                    self.journal[job_name].add_file_event(
                        file.name, "Resumed after app-restart."
                    )
                    self.start_download(job_name, file.name)

            for file in files:
                if file.status == FileModel.STATUS_QUEUED:
                    logger.info(
                        "File %s was queued at last app run, will re-queue now.",
                        file.name,
                    )
                    self.journal[job_name].add_file_event(
                        file.name, "Re-queued after app-restart."
                    )
                    self.start_download(job_name, file.name)

            for file in files:
                if file.status == FileModel.STATUS_COMPLETED:
                    local_size = get_local_file_size(file.target_path)
                    if file.downloaded_bytes is None:
                        logger.error(
                            'Database apparently corrupted for file "%s", downloaded_bytes unset, despite marked as complete.',
                            file.name,
                        )
                        continue
                    if local_size == -1:
                        file.status = FileModel.STATUS_INVALID
                        self.journal[job_name].add_file_event(
                            file.name, "Local file is missing."
                        )
                    elif local_size < file.downloaded_bytes:
                        file.status = FileModel.STATUS_INVALID
                        self.journal[job_name].add_file_event(
                            file.name, "Local file corrupted (smaller than expected)."
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
        if job_name not in self.job_downloaders:
            self.__setup_downloader(job_name)

        queue = self.job_downloaders[job_name]
        queue.start_download_threads()

        if file_name in queue.files_in_queue:
            return False, "File is already downloading."
        if file_name in queue.files_downloading:
            return False, "File is already queued."
        file_dto = self.get_file_dto(job_name, file_name)
        self.job_downloaders[job_name].download_file(file_dto)
        self.__journal_of_job(job_name).update_file_status(
            file_name=file_name, status=FileModel.STATUS_QUEUED
        )
        return True, FileModel.STATUS_QUEUED

    def stop_download(
        self, job_name: str, file_name: str, completion_event=None, add_to_journal=True
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
                file_name=file_name, status=FileModel.STATUS_STOPPED
            )
        return True, "Stopped"

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
                return False, "Could not delete file from disk."

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

    def __setup_downloader(
        self,
        job_name: str,
        start_downloads: bool = False,
        files_with_unknown_size: list = None,
    ) -> None:
        """Setup the downloader for the given job"""
        if job_name not in self.job_downloaders:
            job_dto = None
            with self.db_lock:
                job = get_job_dao().get_job_by_name(job_name)
                job_dto = JobDTO.from_model(job)
            if job_dto is None:
                raise ValueError("Unknown job: " + job_name)
            download_monitor = MainWindowJobMonitor(self, job_dto)
            self.download_monitors[job_name] = download_monitor
            downloader = QueuedDownloader(job=job, monitor=self.monitor_daemon)
            self.job_downloaders[job_name] = downloader

        if files_with_unknown_size is not None:
            downloader.resolve_file_sizes(files_with_unknown_size)
        if start_downloads:
            downloader.start_download_threads()

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

    # TODO refactor this out of here. There should be a central update cycle handler
    def process_job_updates(self, cycle_job_updates: JobUpdates, merge=True) -> None:
        """Process the cycle updates"""
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

        # update db
        with self.db_lock:
            # merge job updates into db
            job = get_job_dao().get_job_by_name(job_name)
            if job_updates.job_update is not None:
                job_updates.job_update.merge_into_model(job)

            # merge file model updates into db
            for file_model_dto in job_updates.file_model_updates.values():
                job_id = get_job_dao().get_job_by_name(job_name).id
                file_model = get_file_model_dao().get_file_model_by_name(
                    job_id, file_model_dto.name
                )
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
                        job_updates.file_model_updates[
                            file_name
                        ].last_event = event.event
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

            # commit db
            get_job_dao().save_job(job)

        # selectively update ui
        if job_updates.job_update is not None:
            self.main_window.update_job_status_signal.emit(
                job_name,
                job_updates.job_update.status,
                job_updates.job_update.get_latest_history_timestamp(),
                job_updates.job_update.get_latest_history_entry().event,
            )

        for file_model_dto in job_updates.file_model_updates.values():
            self.main_window.update_file_signal.emit(file_model_dto)
