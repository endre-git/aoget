import logging
from db.aogetdb import get_job_dao, get_file_model_dao, get_file_event_dao
from model.job_updates import JobUpdates
from model.job import Job
from model.file_model import FileModel
from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO
from controller.derived_field_calculator import DerivedFieldCalculator

logger = logging.getLogger(__name__)


class UpdateCycle:
    """The one-second update tick is handled here. This class is responsible for processing the
    updates from the downloaders and updating the database and the UI. It also updates the rate
    limits. The journal of each job is kept here. The journal is a collection of updates for a job
    that are processed in a single tick. The journal is then cleared. The journal is used to
    aggregate updates for a job that come in from different threads. The journal is then processed
    in a single thread. This class is also responsible for updating the rate limits. The rate limits
    are updated based on the total number of threads that are active."""

    def __init__(self, app_state_handlers, main_window):
        """Create an update cycle handler."""
        self.journal = {}
        self.app = app_state_handlers
        self.main_window = main_window

    def journal_of_job(self, job_name: str) -> JobUpdates:
        """Get the journal of a job.
        :param job_name:
            The name of the job
        :return:
            The job's journal"""
        if job_name not in self.journal:
            self.journal[job_name] = JobUpdates(job_name)
        return self.journal[job_name]

    def create_journal(self, job_name: str) -> None:
        """Create the journal of a job if it does not exist.
        :param job_name:
            The name of the job"""
        if job_name not in self.journal:
            self.journal[job_name] = JobUpdates(job_name)

    def drop_job(self, job_name: str) -> None:
        """Drop the journal of a job if it exists.
        :param job_name:
            The name of the job"""
        if job_name in self.journal:
            del self.journal[job_name]

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

    def __update_job_in_db(
        self, job_name: str, job_updates: JobUpdates, derived_status: str
    ) -> Job:
        """Update the job in the database as per the in-cycle job updates."""
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
        return job

    def __update_file_model_in_db(
        self, job: Job, file_model_dto: FileModelDTO
    ) -> FileModelDTO:
        """Update the file model in the database as per the in-cycle file model updates."""
        job_id = job.id
        file_model = get_file_model_dao().get_file_model_by_name(
            job_id, file_model_dto.name
        )
        db_size = file_model.size_bytes if file_model else 0
        if (
            file_model_dto.size_bytes is not None
            and db_size is None
            or db_size <= 0
            and db_size != file_model_dto.size_bytes
        ):
            job.selected_files_with_known_size += 1
            job.total_size_bytes += file_model_dto.size_bytes
        if file_model is None:
            if file_model_dto.deleted:
                logger.warn(
                    "Tried to delete an already deleted file model: %s",
                    file_model_dto.name,
                )
            else:
                # TODO create and add the new model, and set it to file_model_dto
                logger.error("Tried to update non-existent file.")
        else:
            file_model_dto.merge_into_model(file_model)

        if file_model is not None:
            # back-populate DTO fields from DB for UI display
            file_model_dto.update_from_model(file_model)
        return file_model_dto

    def __update_file_events_in_db(
        self, job: Job, file_name: str, job_updates: JobUpdates, event_dtos: list
    ) -> None:
        """Update the file events in the database as per the in-cycle file event updates."""
        file_model_of_event = get_file_model_dao().get_file_model_by_name(
            job.id, file_name
        )
        if file_model_of_event is None:
            logger.error("File model not found for file event: %s", file_name)
            return
        for event_dto in event_dtos:
            event = event_dto.build_model(file_model_of_event)
            get_file_event_dao().add_file_event(event, commit=False)
            if file_name in job_updates.file_model_updates:
                job_updates.file_model_updates[file_name].last_event = event.event
                job_updates.file_model_updates[file_name].last_event_timestamp = (
                    event.timestamp
                )
        if file_name not in job_updates.file_model_updates:
            # backpopulate to update object for UI display
            job_updates.file_model_updates[file_name] = FileModelDTO.from_model(
                file_model_of_event, job.name
            )

    def __back_populate_file_updates(
        self, job: Job, file_model_dto: FileModelDTO, job_updates: JobUpdates
    ) -> None:
        """Updates are always partial, so we need to back-populate the cached DTOs with the
        full state from the DB."""
        cache = self.app.cache
        job_name = job.name
        file_model = get_file_model_dao().get_file_model_by_name(
            job.id, file_model_dto.name
        )
        if file_model is None:
            logger.error(
                "File model not found for file model DTO: %s",
                file_model_dto.name,
            )
            return
        file_model_dto.update_from_model(file_model)

        # sync up the local cache state
        if not cache.is_cached_job(job_name):
            logger.warn("Job %s not in state cache, assumably got deleted", job_name)
            return
        if not file_model_dto.selected and cache.is_cached_file(
            job_name, file_model_dto.name
        ):
            cache.drop_file(job_name, file_model_dto.name)
            DerivedFieldCalculator.file_deselected_in_job(
                job_updates.job_update, file_model_dto
            )
            job_updates.job_update.merge_into_model(job)
        else:
            cache.set_cached_file(job_name, file_model_dto.name, file_model_dto)

    def __update_cached_job_fields(self, job: Job, job_updates: JobUpdates) -> None:
        """Update the cached fields of the job object both in DB and in cached DTO."""
        # back-populate cached fields to job update DTO for UI display
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

    def process_job_updates(self, cycle_job_updates: JobUpdates, merge=True) -> None:
        app = self.app
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

        derived_status = (
            Job.STATUS_RUNNING
            if app.downloads.is_job_downloading(job_name)
            else Job.STATUS_NOT_RUNNING
        )
        active_thread_count = app.downloads.get_active_thread_count(job_name)
        allocated_thread_count = app.downloads.get_allocated_thread_count(job_name)

        # update db
        with app.db_lock:
            # merge job updates into db
            job = self.__update_job_in_db(job_name, job_updates, derived_status)

            job_updates.job_update.threads_active = active_thread_count
            job_updates.job_update.threads_allocated = allocated_thread_count

            # merge file model updates into db
            for file_model_dto in job_updates.file_model_updates.values():
                self.__update_file_model_in_db(job, file_model_dto)

            for file_name, event_dtos in job_updates.file_event_updates.items():
                self.__update_file_events_in_db(job, file_name, job_updates, event_dtos)

            # back-populate most recent file event to every file model DTO for UI display
            for file_model_dto in job_updates.file_model_updates.values():
                self.__back_populate_file_updates(job, file_model_dto, job_updates)

            self.__update_cached_job_fields(job, job_updates)

            # commit db
            get_job_dao().save_job(job)

        # selectively update ui
        if job_updates.job_update is not None:
            if app.downloads.is_job_resuming(job_name):
                job_updates.job_update.status = "Resuming"
            self.main_window.update_job_signal.emit(job_updates.job_update)
        for file_model_dto in job_updates.file_model_updates.values():
            self.main_window.update_file_signal.emit(file_model_dto)

    def __update_rate_limits(self) -> None:
        """Update the rate limits"""
        total_thread_count = 0
        dls = self.app.downloads
        for job in dls.get_all_active_job_names():
            total_thread_count += dls.get_downloader(job).get_active_thread_count()
        if total_thread_count == 0:
            return
        per_thread_limit = self.app.rate_limiter.get_per_thread_limit(
            total_thread_count
        )
        for job in dls.get_all_active_job_names():
            dls.get_downloader(job).set_rate_limit(per_thread_limit)
