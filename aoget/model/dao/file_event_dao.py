from sqlalchemy.orm import sessionmaker
from aoget.model import FileEvent


class FileEventDAO:

    """Data access object for FileEvents."""
    def __init__(self, Session: sessionmaker):
        self.Session = Session

    def add_file_event(self, file_id, message):
        """Add a FileEvent to the database.
        :param file_id:
            The ID of the file the event is for.
        :param message:
            The message to log."""
        try:
            with self.Session() as session:
                file_event = FileEvent(file_id=file_id, message=message)
                session.add(file_event)
                session.commit()
        except Exception as e:
            print(f"Error adding FileEvent to the database: {e}")

    def get_file_events_by_file_id(self, file_id):
        """Get all FileEvents for a file.
        :param file_id:
            The ID of the file to get events for.
        :return:
            A list of FileEvents."""
        with self.Session() as session:
            return session.query(FileEvent).filter_by(file_id=file_id).all()
