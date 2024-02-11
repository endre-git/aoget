import logging
from collections import defaultdict
import threading
from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO
from model.dto.file_event_dto import FileEventDTO
from model.file_model import FileModel
from util.aogetutil import timestamp_str, human_filesize, human_priority

logger = logging.getLogger(__name__)


class JobUpdates:
    """This is a journal of changes. It is used to update the database in a single run
    instead of having plenty of small transactions. It also allows a drastically
    simplified database session management and the use of immutable objects in the app.
    """

    def __init__(self, job_name: str):
        self.job_name = job_name
        self.job_update = None
        self.file_model_updates = {}
        self.file_event_updates = defaultdict(list)
        self.lock = threading.RLock()

    def clear(self) -> None:
        """Clear all updates."""
        self.job_update = None
        self.file_model_updates = {}
        self.file_event_updates = defaultdict(list)

    def snapshot(self) -> tuple:
        """Create a snapshot of the current journal. This is deepcopy, but only a subset of
        data that are needed for derived field calculations."""
        snapshot = JobUpdates(self.job_name)
        if self.job_update is not None:
            snapshot.job_update = JobDTO(
                id=self.job_update.id,
                name=self.job_update.name,
                page_url=self.job_update.page_url,
                status=self.job_update.status,
                total_size_bytes=self.job_update.total_size_bytes,
                target_folder=self.job_update.target_folder,
                deleted=self.job_update.deleted,
            )
        for file_model_update in self.file_model_updates.values():
            snapshot.file_model_updates[file_model_update.name] = FileModelDTO(
                job_name=file_model_update.job_name,
                name=file_model_update.name,
                extension=file_model_update.extension,
                selected=file_model_update.selected,
                url=file_model_update.url,
                size_bytes=file_model_update.size_bytes,
                downloaded_bytes=file_model_update.downloaded_bytes,
                status=file_model_update.status,
                rate_bytes_per_sec=file_model_update.rate_bytes_per_sec,
                eta_seconds=file_model_update.eta_seconds,
                percent_completed=file_model_update.percent_completed,
                last_event_timestamp=file_model_update.last_event_timestamp,
                last_event=file_model_update.last_event,
                deleted=file_model_update.deleted,
            )
        # no need to copy file events as no value is derived from them
        return snapshot

    def merge(self, other) -> None:
        """Merge the other journal into this one. This is used for incremental updates."""
        with self.lock:
            if other.job_update:
                if self.job_update:
                    self.job_update.merge(other.job_update)
                else:
                    self.job_update = other.job_update
            for file_name, file_model_update in self.file_model_updates.items():
                if file_name in other.file_model_updates:
                    file_model_update.merge(other.file_model_updates[file_name])
            for file_model_update in other.file_model_updates.values():
                if file_model_update.name in self.file_model_updates:
                    self.file_model_updates[file_model_update.name].merge(
                        file_model_update
                    )
                else:
                    self.file_model_updates[file_model_update.name] = file_model_update
            for file_name, file_event_updates in other.file_event_updates.items():
                self.file_event_updates[file_name].extend(file_event_updates)

    def add_job_update(self, job_dto: JobDTO) -> None:
        """Add a job update to the journal.
        :param job_dto: The job update to add to the journal."""
        self.job_update = job_dto

    def update_job_threads(self, threads_allocated: int, threads_active: int) -> None:
        """Update the number of threads allocated and active for the job.
        :param threads_allocated: The number of threads allocated
        :param threads_active: The number of threads active"""
        if not self.job_update:
            self.job_update = JobDTO(
                id=-1,
                name=self.job_name,
                threads_allocated=threads_allocated,
                threads_active=threads_active,
            )
        else:
            self.job_update.threads_allocated = threads_allocated
            self.job_update.threads_active = threads_active

    def add_file_model_update(self, file_model_dto: FileModelDTO) -> None:
        """Add a file model update to the journal.
        :param file_model_dto: The file model update to add to the journal."""
        self.file_model_updates[file_model_dto.name] = file_model_dto

    def add_file_event_update(self, file_event_dto: FileEventDTO) -> None:
        """Add a file event update to the journal.
        :param file_event_dto: The file event update to add to the journal."""
        self.file_event_updates[file_event_dto.name].append(file_event_dto)

    def incremental_job_update(self, job_dto: JobDTO) -> None:
        """Add an incremental job update to the journal.
        :param job_dto: The job update to add to the journal."""
        if self.job_update:
            self.job_update.merge(job_dto)
        else:
            self.job_update = job_dto

    def incremental_file_model_update(self, file_model_dto: FileModelDTO) -> None:
        """Add an incremental file model update to the journal.
        :param file_model_dto: The file model update to add to the journal."""
        if file_model_dto.name in self.file_model_updates:
            self.file_model_updates[file_model_dto.name].merge(file_model_dto)
        else:
            self.file_model_updates[file_model_dto.name] = file_model_dto

    def add_file_event(self, file_name: str, event: str) -> None:
        """Add a file event to the journal.
        :param file_name: The name of the file the event is for
        :param file_event_dto: The file event to add to the journal."""
        with self.lock:
            file_event_dto = FileEventDTO(timestamp=timestamp_str(), event=event)
            self.file_event_updates[file_name].append(file_event_dto)

    def update_file_download_progress(
        self, file_name: str, written: int, total: int
    ) -> None:
        """Update the download progress of a file.
        :param file_name: The name of the file to update
        :param written: The number of bytes written
        :param total: The total number of bytes to write"""
        if file_name in self.file_model_updates:
            self.file_model_updates[file_name].downloaded_bytes = written
            self.file_model_updates[file_name].size_bytes = total
        else:
            self.file_model_updates[file_name] = FileModelDTO(
                job_name=self.job_name,
                name=file_name,
                downloaded_bytes=written,
                size_bytes=total,
            )

    def update_file_status(self, file_name: str, status: str, err: str = "") -> None:
        """Update the status of a file.
        :param file_name: The name of the file to update
        :param status: The new status of the file"""
        if file_name in self.file_model_updates:
            self.file_model_updates[file_name].status = status
        else:
            self.file_model_updates[file_name] = FileModelDTO(
                job_name=self.job_name, name=file_name, status=status
            )
        if status == FileModel.STATUS_COMPLETED:
            self.add_file_event(file_name, "Completed downloading.")
        elif status == FileModel.STATUS_FAILED:
            self.add_file_event(file_name, f"Failed, reason: {err}.")
        elif status == FileModel.STATUS_STOPPED:
            self.add_file_event(file_name, "Stopped downloading.")
        elif status == FileModel.STATUS_QUEUED:
            self.add_file_event(file_name, "Queued for download.")
        elif status == FileModel.STATUS_DOWNLOADING:
            self.add_file_event(file_name, "Started downloading.")
        elif status == FileModel.STATUS_INVALID:
            self.add_file_event(file_name, "Invalid file.")

    def update_file_size(self, file_name: str, size: int) -> None:
        """Update the size of a file.
        :param file_name: The name of the file to update
        :param size: The new size of the file"""
        if file_name in self.file_model_updates:
            self.file_model_updates[file_name].size_bytes = size
        else:
            self.file_model_updates[file_name] = FileModelDTO(
                job_name=self.job_name, name=file_name, size_bytes=size
            )
        self.add_file_event(file_name, "Resolved size: " + str(human_filesize(size)))

    def update_file_priority(self, file_name: str, priority: int) -> None:
        """Update the priority of a file.
        :param file_name: The name of the file to update
        :param priority: The new priority of the file"""
        if file_name in self.file_model_updates:
            self.file_model_updates[file_name].priority = priority
        else:
            self.file_model_updates[file_name] = FileModelDTO(
                job_name=self.job_name, name=file_name, priority=priority
            )
        self.add_file_event(
            file_name, f"Priority changed to {human_priority(priority)}."
        )

    def deselect_file(self, file_name: str) -> None:
        """Deselect a file.
        :param file_name: The name of the file to deselect"""
        logger.debug(f"Deselecting file {file_name} from {self.job_name}")
        if file_name in self.file_model_updates:
            self.file_model_updates[file_name].selected = False
        else:
            self.file_model_updates[file_name] = FileModelDTO(
                job_name=self.job_name, name=file_name, selected=False
            )
        self.add_file_event(file_name, "Removed from download set.")

    def __str__(self):
        return f"""JobUpdates(job_name={self.job_name},
        job_update={self.job_update},
        file_model_updates={self.file_model_updates},
        file_event_updates={self.file_event_updates})"""

    def __repr__(self):
        return self.__str__()
