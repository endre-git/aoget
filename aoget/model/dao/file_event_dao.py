import logging
import threading
from sqlalchemy.orm import Session
from ..file_event import FileEvent
from ..file_model import FileModel
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class FileEventDAO:
    """Data access object for FileEvents.

    This class provides an interface to perform CRUD operations on FileEvent
    objects within a database using SQLAlchemy. It employs a thread-safe commit
    mechanism to ensure data integrity in concurrent environments."""

    def __init__(self, session: Session, commit_lock: threading.Lock):
        """Create a new FileEventDAO.

        :param session: The SQLAlchemy session to use for database operations.
        """
        self.session = session
        self.commit_lock = commit_lock

    def _commit(self):
        """Perform a thread-safe commit using the commit lock.

        This method handles the commit operation within a lock, ensuring that
        commit operations are thread-safe.
        """
        with self.commit_lock:
            self.session.commit()

    def create_file_event(
        self, event: str, file_model: FileModel, commit: bool = True
    ) -> FileEvent:
        """Add a new FileEvent to the database.

        :param event: The event to add.
        :param file_model: The FileModel associated with the event.
        :param commit: Whether to commit the transaction (default is True).
        :return: The newly created FileEvent object.
        """
        new_event = FileEvent(event=event, file=file_model)
        self.session.add(new_event)
        if commit:
            try:
                self._commit()
            except SQLAlchemyError as e:
                logger.error(f"Error committing FileEvent creation: {e}")
                raise e
        return new_event

    def add_file_event(self, file_event: FileEvent, commit: bool = True) -> None:
        """Add a new FileEvent to the database.

        :param file_event: The FileEvent object to add to the database.
        :param commit: Whether to commit the transaction (default is True).
        """
        self.session.add(file_event)
        if commit:
            try:
                self._commit()
            except SQLAlchemyError as e:
                logger.error(f"Error committing FileEvent addition: {e}")
                raise e

    def get_file_events_by_file_id(self, file_id: int) -> list:
        """Retrieve all FileEvents associated with a given file ID.

        :param file_id: The ID of the file to retrieve events for.
        :return: A list of FileEvent objects.
        """
        return self.session.query(FileEvent).filter(FileEvent.file_id == file_id).all()

    def get_file_event_by_id(self, event_id: int) -> FileEvent:
        """Retrieve a FileEvent by its ID.

        :param event_id: The ID of the FileEvent to retrieve.
        :return: The requested FileEvent object, or None if not found.
        """
        return self.session.query(FileEvent).filter(FileEvent.id == event_id).first()

    def delete_file_event(self, event_id: int, commit: bool = True) -> None:
        """Delete a FileEvent by its ID.

        :param event_id: The ID of the FileEvent to delete.
        :param commit: Whether to commit the transaction (default is True).
        """
        file_event = self.session.query(FileEvent).filter_by(id=event_id).first()
        if file_event:
            self.session.delete(file_event)
            if commit:
                try:
                    self._commit()
                except SQLAlchemyError as e:
                    logger.error(f"Error committing FileEvent deletion: {e}")
                    raise e

    def delete_file_events_by_file_id(self, file_id: int, commit: bool = True) -> None:
        """Delete all FileEvents associated with a given file ID.

        :param file_id: The ID of the file for which to delete events.
        :param commit: Whether to commit the transaction (default is True).
        """
        file_events = self.session.query(FileEvent).filter_by(file_id=file_id).all()
        for file_event in file_events:
            self.session.delete(file_event)
        if commit:
            try:
                self._commit()
            except SQLAlchemyError as e:
                logger.error(f"Error committing FileEvents deletion: {e}")
                raise e
