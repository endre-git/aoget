from sqlalchemy.orm import Session
from ..file_event import FileEvent
from ..file_model import FileModel


class FileEventDAO:
    """Data access object for FileEvents."""

    def __init__(self, session: Session):
        self.session = session

    def create_file_event(self, event: str, file_model: FileModel, commit: bool = True) -> FileEvent:
        """Add a new FileEvent to the database using the bare minimum parameter set.
        :param event: The event to add
        :param file_id: The ID of the file the event is for
        :param commit: Whether to commit the transaction
        :return: The newly created FileEvent"""
        new_event = FileEvent(event=event, file=file_model)
        self.session.add(new_event)
        if commit:
            self.session.commit()
        return new_event

    def add_file_event(self, file_event: FileEvent, commit: bool = True) -> None:
        """Add a new FileEvent to the database.
        :param file_event: The FileEvent to add
        :param commit: Whether to commit the transaction"""
        self.session.add(file_event)
        if commit:
            self.session.commit()

    def get_file_events_by_file_id(self, file_id: int) -> list:
        """Get all FileEvents for the given file ID.
        :param file_id: The ID of the file to get events for
        :return: A list of FileEvents"""
        return self.session.query(FileEvent).filter(FileEvent.file_id == file_id).all()

    def get_file_event_by_id(self, event_id: int) -> FileEvent:
        """Get a FileEvent by its ID.
        :param event_id: The ID of the FileEvent to get
        :return: The FileEvent"""
        return self.session.query(FileEvent).filter(FileEvent.id == event_id).first()

    def delete_file_event(self, event_id: int, commit: bool = True) -> None:
        """Delete a FileEvent.
        :param event_id: The ID of the FileEvent to delete
        :param commit: Whether to commit the transaction"""
        file_event = self.session.query(FileEvent).filter_by(id=event_id).first()
        if file_event:
            self.session.delete(file_event)
            if commit:
                self.session.commit()

    def delete_file_events_by_file_id(self, file_id: int, commit: bool = True) -> None:
        """Delete all FileEvents for the given file ID.
        :param file_id: The ID of the file to delete events for
        :param commit: Whether to commit the transaction"""
        file_events = self.session.query(FileEvent).filter_by(file_id=file_id).all()
        for file_event in file_events:
            self.session.delete(file_event)
        if commit:
            self.session.commit()
