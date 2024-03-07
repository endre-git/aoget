import threading
import time
import logging
from model.job_updates import JobUpdates
from controller.derived_field_calculator import DerivedFieldCalculator

logger = logging.getLogger(__name__)


class JournalDaemon:
    """A thread-safe progress reporter that reports progress of multiple event sources - firing on
    different threads - on a single thread. Also implements throttling of progress updates to
    avoid stale update reporting."""

    def __init__(
        self,
        update_interval_seconds: int = 1,
        journal_processor: any = None,
        start_daemon: bool = True,
    ):
        """Create a progress reporter.
        :param job_monitor:
            The job monitor to report progress to. If None, no progress will be reported.
        """
        self.update_interval_seconds = update_interval_seconds
        self.__lock = threading.RLock()
        self.__journal_processor = journal_processor
        self.__stopped = False
        self.__journal = {}  # type: Dict[str, JobUpdates]
        # holds the previous snapshot of the journal to calculate derived fields
        self.__snapshot = {}  # type: Dict[str, JobUpdates]
        flush_thread = threading.Thread(target=self.__append_journal, daemon=True)
        if start_daemon:
            flush_thread.start()

    def __append_journal(self) -> None:
        """Update the observers with the current progress."""
        logger.info('Journal daemon started.')
        while not self.__stopped:
            if self.__journal_processor is not None:
                with self.__lock:
                    # calculate the derived fields using the previous snapshot
                    if len(self.__snapshot) > 0:
                        DerivedFieldCalculator.patch(self.__journal, self.__snapshot)
                    if len(self.__journal) > 0:
                        for jobname in self.__journal:
                            self.__snapshot[jobname] = self.__journal[
                                jobname
                            ].snapshot()
                    self.__journal_processor.update_tick(self.__journal)
                    self.__journal.clear()
            time.sleep(self.update_interval_seconds)
        logger.info('Journal daemon stopped.')

    def update_download_progress(
        self, jobname: str, filename: str, written: int, total: int
    ) -> None:
        """Update the progress of the given filename.
        :param jobname:
            The name of the job
        :param filename:
            The filename to update
        :param written:
            Bytes written so far
        :param total:
            Total bytes to write"""
        with self.__lock:
            self.__journal_of_job(jobname).update_file_download_progress(
                filename, written, total
            )

    def update_file_status(
        self, jobname: str, filename: str, status: str, err: str = ""
    ) -> None:
        """Update the status of the given filename.
        :param jobname:
            The name of the job
        :param filename:
            The filename to update
        :param status:
            The status to update"""
        with self.__lock:
            self.__journal_of_job(jobname).update_file_status(filename, status, err)

    def update_file_size(self, jobname: str, filename: str, size: int) -> None:
        """Update the size of the given filename.
        :param jobname:
            The name of the job
        :param filename:
            The filename to update
        :param size:
            The size to update"""
        with self.__lock:
            self.__journal_of_job(jobname).update_file_size(filename, size)

    def add_file_events(self, jobname: str, events: dict) -> None:
        """Add events to the given filename.
        :param jobname:
            The name of the job
        :param events:
            The events to add in a dict of filename: event list pairs"""
        with self.__lock:
            self.__journal_of_job(jobname).add_file_events(events)

    def add_file_event(self, jobname: str, filename: str, event: str) -> None:
        """Add an event to the given filename.
        :param jobname:
            The name of the job
        :param filename:
            The filename to update
        :param event:
            The event to add"""
        with self.__lock:
            self.__journal_of_job(jobname).add_file_event(filename, event)

    def update_job_downloaded_bytes(self, jobname: str, downloaded_bytes: int) -> None:
        """Update the downloaded bytes of the given job.
        :param jobname:
            The name of the job
        :param downloaded_bytes:
            The downloaded bytes to update"""
        with self.__lock:
            self.__journal_of_job(jobname).update_job_downloaded_bytes(downloaded_bytes)

    def update_job_files_done(self, jobname: str, files_done: int) -> None:
        """Update the files done of the given job.
        :param jobname:
            The name of the job
        :param files_done:
            The files done to update"""
        with self.__lock:
            self.__journal_of_job(jobname).update_job_files_done(files_done)

    def drop_job(self, jobname: str) -> None:
        """Drop the given job from the journal.
        :param jobname:
            The name of the job"""
        with self.__lock:
            if jobname in self.__journal:
                self.__journal.pop(jobname, None)

    def __journal_of_job(self, jobname: str) -> JobUpdates:
        """Get the journal of a job.
        :param jobname:
            The name of the job
        :return:
            The job's journal"""
        with self.__lock:
            if jobname not in self.__journal:
                self.__journal[jobname] = JobUpdates(jobname)
            return self.__journal[jobname]

    def stop(self):
        """Stop the progress reporter."""
        self.__stopped = True
