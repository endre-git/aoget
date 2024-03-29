import logging
import os
from typing import List
from urllib.parse import unquote
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from . import Base
from .file_event import FileEvent

logger = logging.getLogger(__name__)


class FileModel(Base):
    """A file entry in a fileset. Mutable."""

    __tablename__ = "file_model"

    STATUS_NEW = "New"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_QUEUED = "In queue"
    STATUS_COMPLETED = "Completed"
    STATUS_FAILED = "Failed"
    STATUS_STOPPING = "Stopping"
    STATUS_STOPPED = "Stopped"
    STATUS_INVALID = "Invalid"

    PRIORITY_HIGH = 1
    PRIORITY_NORMAL = 2
    PRIORITY_LOW = 3

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    extension: Mapped[str] = mapped_column(nullable=False)
    selected: Mapped[bool] = mapped_column(default=False, nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=True, default=-1)
    downloaded_bytes: Mapped[int] = mapped_column(nullable=True, default=-1)
    status: Mapped[str] = mapped_column(default=STATUS_NEW)
    priority: Mapped[int] = mapped_column(default=2, nullable=False)
    history_entries: Mapped[List["FileEvent"]] = relationship(
        back_populates="file", cascade="all, delete, delete-orphan"
    )
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id", ondelete="CASCADE"))
    job: Mapped["Job"] = relationship(back_populates="files")  # noqa: F821

    def __init__(self, job, url):
        self.name = unquote(url.split("/")[-1])
        if "." in self.name:
            self.extension = self.name.split(".")[-1]
        else:
            self.extension = ""
        self.url = url
        self.status = FileModel.STATUS_NEW
        FileEvent("Added.", self)
        self.job = job

    def __repr__(self):
        return "<FileModel(name='%s', url='%s')>" % (self.name, self.url)

    def has_history(self) -> bool:
        """Determine whether this file has any history entries.
        :return:
            True if this file has history entries, False otherwise"""
        return len(self.history_entries) > 0

    def get_latest_history_timestamp(self) -> int:
        """Get the timestamp of the latest history entry.
        :return:
            The timestamp of the latest history entry, or None if there are no history entries
        """
        if not self.has_history():
            return None
        return self.get_latest_history_entry().timestamp

    def get_latest_history_entry(self) -> FileEvent:
        """Get the latest history entry.
        :return:
            The latest history entry, or None if there are no history entries"""
        if not self.has_history():
            return None
        return max(
            self.history_entries, key=lambda event: event.timestamp, default=None
        )

    def get_target_path(self) -> str:
        """Get the target path of the file.
        :return:
            The target path of the file"""
        if self.job.target_folder is None:
            raise ValueError("Job target folder is None")
        return os.path.join(self.job.target_folder, self.name)

    def add_event(self, message: str) -> None:
        """Add a history event.
        :param message:
            The message to add"""
        self.history_entries.append(FileEvent(message, self))

    def validate_downloaded(self) -> int:
        """Check on disk if the file has been downloaded successfully."""
        if not os.path.exists(self.get_target_path()):
            return -1
        return os.path.getsize(self.get_target_path())
