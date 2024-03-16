import logging
from db.aogetdb import get_job_dao, get_file_model_dao, get_file_event_dao
from model.job_updates import JobUpdates
from model.job import Job
from model.file_model import FileModel
from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO
from controller.derived_field_calculator import DerivedFieldCalculator
from util.runtime_stats import RuntimeStats

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
        self.tick_count = 0
        self.stats = RuntimeStats()

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

    def update_tick(self, async_journal: dict):
        """Called by the ticker to process the updates"""
        self.stats.check_in("tick")
        self.tick_count += 1
        # join the keysets of the journal and the current job updates
        all_job_names = set(async_journal.keys()).union(set(self.journal.keys()))
        for jobname in all_job_names:
            with self.app.job_lock(jobname):
                self.stats.check_in("process_job_updates")
                if jobname in async_journal and jobname in self.journal:
                    self.process_job_updates(async_journal[jobname], merge=True)
                elif jobname in self.journal:
                    self.process_job_updates(self.journal[jobname], merge=False)
                else:
                    self.process_job_updates(async_journal[jobname], merge=True)
                self.stats.check_out("process_job_updates")
        self.journal.clear()
        self.__update_rate_limits()
        self.stats.check_out("tick")
        logger.debug(f"Tick #{self.tick_count} stats: totals={self.stats.get_totals()}")

    def __update_job_in_db(self, job_name: str, job_updates: JobUpdates) -> Job:
        """Update the job in the database as per the in-cycle job updates."""
        self.stats.check_in("__update_job_in_db")
        job = get_job_dao().get_job_by_name(job_name)
        if job is None:
            logger.debug("Stale job update for: %s", job_name)
            return
        job.status = (
            job_updates.job_update.status
            if job_updates.job_update and job_updates.job_update.status
            else job.status
        )
        if job_updates.job_update is not None:
            job_updates.job_update.merge_into_model(job)
            job_updates.job_update.update_from_model(job)
        else:
            job_updates.job_update = JobDTO.from_model(job)
        self.stats.check_out("__update_job_in_db")
        return job

    def __preload_files(self, job: Job, file_names: set) -> dict:
        """Preload the file models from the database for the given job and file names."""
        self.stats.check_in("__preload_files")
        cached_file_models = {}
        for file_name in file_names:
            self.stats.check_in("get_file_model_by_name")
            cached_file_models[file_name] = get_file_model_dao().get_file_model_by_name(
                job.id, file_name
            )
            self.stats.check_out("get_file_model_by_name")
        self.stats.check_out("__preload_files")
        return cached_file_models

    def __update_file_model(
        self, job: Job, file_model_dto: FileModelDTO, cached_file_models: dict
    ) -> FileModel:
        """Update the file model in the database as per the in-cycle file model updates."""
        self.stats.check_in("__update_file_model_in_db")
        job_id = job.id
        self.stats.check_in("get_file_model_by_name")
        file_model = (
            cached_file_models[file_model_dto.name]
            if file_model_dto.name in cached_file_models
            else get_file_model_dao().get_file_model_by_name(
                job_id, file_model_dto.name
            )
        )
        self.stats.check_out("get_file_model_by_name")
        db_size = file_model.size_bytes if file_model else 0
        if (
            file_model_dto.size_bytes is not None and file_model_dto.size_bytes > -1
        ) and (db_size is None or db_size < 0):
            job.selected_files_with_known_size = (
                1
                if job.selected_files_with_known_size is None
                else job.selected_files_with_known_size + 1
            )
            job.total_size_bytes = (
                file_model_dto.size_bytes
                if job.total_size_bytes is None
                else job.total_size_bytes + file_model_dto.size_bytes
            )
        if file_model is None:
            if file_model_dto.deleted:
                logger.warn(
                    "Tried to delete an already deleted file model: %s",
                    file_model_dto.name,
                )
            else:
                logger.error(
                    "Tried to update non-existent file: "
                    + file_model_dto.name
                    + " in job "
                    + job.name
                )
        else:
            self.stats.check_in("merge_into_model")
            file_model_dto.merge_into_model(file_model)
            self.stats.check_out("merge_into_model")

        self.stats.check_in("merge (with cache)")
        if self.app.cache.is_cached_file(job.name, file_model_dto.name):
            cached_file = self.app.cache.get_cached_file(job.name, file_model_dto.name)
            cached_file.merge(file_model_dto)
            file_model_dto.merge(cached_file)
        self.stats.check_out("merge (with cache)")
        self.stats.check_out("__update_file_model_in_db")
        return file_model

    def __update_file_events_in_db(
        self,
        job: Job,
        file_name: str,
        job_updates: JobUpdates,
        event_dtos: list,
        cached_db_file_models: dict,
    ) -> None:
        """Update the file events in the database as per the in-cycle file event updates."""
        self.stats.check_in("__update_file_events_in_db")
        file_model_of_event = (
            cached_db_file_models[file_name]
            if file_name in cached_db_file_models
            else get_file_model_dao().get_file_model_by_name(job.id, file_name)
        )
        if file_model_of_event is None:
            logger.error("File model not found for file event: %s", file_name)
            return
        for event_dto in event_dtos:
            self.stats.check_in("FileEventDTO.build_model")
            event = event_dto.build_model(file_model_of_event)
            self.stats.check_out("FileEventDTO.build_model")
            self.stats.check_in("add_file_event")
            get_file_event_dao().add_file_event(event, commit=False)
            self.stats.check_out("add_file_event")

        most_recent_event = max(event_dtos, key=lambda e: e.timestamp)
        if file_name in job_updates.file_model_updates:
            job_updates.file_model_updates[file_name].last_event = (
                most_recent_event.event
            )
            job_updates.file_model_updates[file_name].last_event_timestamp = (
                most_recent_event.timestamp
            )
        self.stats.check_in("file_model_dto update for evt")
        file_model_dto = self.app.cache.get_cached_file(job.name, file_name)
        file_model_dto.last_event = most_recent_event.event
        file_model_dto.last_event_timestamp = most_recent_event.timestamp
        self.stats.check_out("file_model_dto update for evt")
        self.stats.check_out("__update_file_events_in_db")

    def __update_if_dropped_file(
        self, job: Job, file_model_dto: FileModelDTO, job_updates: JobUpdates
    ) -> None:
        """Dropped files have a special treatment: we need to update the total job
        size."""
        job_name = job.name
        cache = self.app.cache

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

    def __infer_job_status(self, job: Job, job_updates: JobUpdates) -> None:
        """Starting, stopping are transient states, in case the updates all occurred, it's
        the ticker (this method) that sets it back to a steady running / not running state
        """
        if job.status == Job.STATUS_STOPPING:
            stopping_finished = not self.app.downloads.is_job_downloading(job.name)
            if stopping_finished:
                logger.debug(
                    f"""Stopping apparently finished, setting job to 
                    {Job.STATUS_NOT_RUNNING} state."""
                )
                job.status = Job.STATUS_NOT_RUNNING
                job_updates.job_update.status = Job.STATUS_NOT_RUNNING
        elif job.status == Job.STATUS_STARTING:
            files = self.app.cache.get_cached_files(job.name)
            inactive_files = [
                file
                for file in files.values()
                if file.status
                in [
                    FileModel.STATUS_FAILED,
                    FileModel.STATUS_STOPPED,
                    FileModel.STATUS_NEW,
                ]
            ]
            if len(inactive_files) == 0:
                logger.debug(
                    f"""Starting apparently finished, setting job to 
                    {Job.STATUS_RUNNING} state."""
                )
                job.status = Job.STATUS_RUNNING
                job_updates.job_update.status = Job.STATUS_RUNNING
        else:
            derived_status = (
                Job.STATUS_RUNNING
                if self.app.downloads.is_job_downloading(job.name)
                else Job.STATUS_NOT_RUNNING
            )
            job.status = derived_status
            job_updates.job_update.status = derived_status

    def __update_calculated_job_fields(self, job: Job, job_updates: JobUpdates) -> None:
        """Update the cached fields of the job object both the model and the DTO."""
        job_dto = job_updates.job_update
        # back-populate cached fields to job update DTO for UI display
        job_dto.total_size_bytes = job.total_size_bytes
        job_dto.selected_files_with_known_size = job.selected_files_with_known_size
        if job.selected_files_count is None or job.selected_files_count < 0:
            job.selected_files_count = len(self.app.cache.get_files_of_job(job.name))
        job_dto.selected_files_count = job.selected_files_count

        # downloaded bytes is a cache field, so we need to update it in the job object
        downloaded_bytes = (
            # sum up the downloaded bytes of all files in cache
            sum(
                file.downloaded_bytes
                for file in self.app.cache.get_cached_files(job.name).values()
                if file.downloaded_bytes is not None
            )
        )
        job.downloaded_bytes = downloaded_bytes
        job_dto.downloaded_bytes = downloaded_bytes

        # downloaded files count
        completed_files = (
            # count the files that are completed in cache
            sum(
                1
                for file in self.app.cache.get_cached_files(job.name).values()
                if file.status == FileModel.STATUS_COMPLETED and file.selected
            )
        )
        job.files_done = job_dto.files_done = completed_files
        if job.files_done == job.selected_files_count:
            job.status = job_dto.status = Job.STATUS_COMPLETED

        job_dto.size_resolver_status = (
            "Running"
            if self.app.downloads.is_job_size_resolving(job.name)
            else "Not running"
        )
        if job.status != Job.STATUS_COMPLETED:
            self.__infer_job_status(job, job_updates)

    def process_job_updates(self, cycle_job_updates: JobUpdates, merge=True) -> None:
        app = self.app
        """Process the cycle updates for a single job."""
        job_name = cycle_job_updates.job_name
        if merge:
            job_updates = self.journal[job_name] if job_name in self.journal else None
            if job_updates is None:
                job_updates = cycle_job_updates
            else:
                self.stats.check_in("merge_job_updates")
                job_updates.merge(cycle_job_updates)
                self.stats.check_out("merge_job_updates")
        else:
            job_updates = cycle_job_updates

        self.stats.check_in("app_db_locked")
        # update db
        with app.db_lock:
            # merge job updates into db
            job = self.__update_job_in_db(job_name, job_updates)
            if job is None:
                logger.warning(
                    "Skipping journal processing for stale job: %s", job_name
                )
                return
            active_thread_count = app.downloads.get_active_thread_count(job_name)
            allocated_thread_count = app.downloads.get_allocated_thread_count(job_name)

            job_updates.job_update.threads_active = active_thread_count
            job_updates.job_update.threads_allocated = allocated_thread_count

            all_impacted_file_names = set(job_updates.file_model_updates.keys()).union(
                set(job_updates.file_event_updates.keys())
            )

            cached_db_file_models = self.__preload_files(job, all_impacted_file_names)
            for file_model_dto in job_updates.file_model_updates.values():
                self.__update_file_model(job, file_model_dto, cached_db_file_models)
                self.__update_if_dropped_file(job, file_model_dto, job_updates)

            for file_name, event_dtos in job_updates.file_event_updates.items():
                self.__update_file_events_in_db(
                    job, file_name, job_updates, event_dtos, cached_db_file_models
                )

            self.__update_calculated_job_fields(job, job_updates)

            # commit db
            self.stats.check_in("save_job")
            get_job_dao().save_job(job)
            self.stats.check_out("save_job")

        self.stats.check_out("app_db_locked")

        # update UI

        # this is needed so that the updates are UI-propagated as file updates even if 
        # there was only a file event added (that won't show in job_updates.file_updates)
        self.stats.check_in("get_cached_files")
        cached_files = app.cache.get_cached_files(job_name)
        all_impacted_files = {
            file_name: cached_files[file_name] for file_name in all_impacted_file_names
        }
        self.stats.check_out("get_cached_files")

        if job_updates.job_update is not None:
            if app.downloads.is_job_resuming(job_name):
                job_updates.job_update.status = "Resuming"
            self.main_window.update_job_signal.emit(job_updates.job_update)
        self.stats.check_in("update_file_signal")
        for file_model_dto in all_impacted_files.values():
            self.main_window.update_file_signal.emit(file_model_dto)
        self.stats.check_out("update_file_signal")

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
