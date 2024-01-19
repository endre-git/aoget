import logging
from urllib.parse import unquote
from sqlalchemy.orm import Mapped, mapped_column, relationship
from . import Base
from .file_event import FileEvent

logger = logging.getLogger(__name__)


class FileModel(Base):
    """A file entry in a fileset. Mutable."""

    __tablename__ = "file_model"

    STATUS_NEW = "New"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_DOWNLOADED = "Completed"
    STATUS_FAILED = "Failed"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    extension: Mapped[str] = mapped_column(nullable=False)
    selected: Mapped[bool] = mapped_column(default=False, nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(default=STATUS_NEW)
    local_path: Mapped[str]
    history_entries = relationship("FileEvent", back_populates="file")


    def __init__(self, url):
        self.name = unquote(url.split("/")[-1])
        if "." in self.name:
            self.extension = self.name.split(".")[-1]
        else:
            self.extension = ""
        self.url = url
        self.status = FileModel.STATUS_NEW
        self.history_entries.append(FileEvent("Parsed from page"))

    def __repr__(self):
        return "<FileModel(name='%s', url='%s')>" % (self.name, self.url)
