"""Event history entries of a file model."""
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from util.aogetutil import timestamp_str
from . import Base


class FileEvent(Base):
    """Event history entries of a file model."""

    __tablename__ = "file_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("file_model.id"))
    file: Mapped["FileModel"] = relationship(back_populates="history_entries")
    timestamp: Mapped[str] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(nullable=False)

    def __init__(self, message):
        self.message = message
        self.timestamp = timestamp_str()

    def __repr__(self) -> str:
        return "<FileEvent(timestamp='%s', message='%s')>" % (
            self.timestamp,
            self.message,
        )
