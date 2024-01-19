from sqlalchemy.orm import sessionmaker
from aoget.model.file_set import FileSet


class FileSetDAO:
    """Data access object for FileSets."""

    def __init__(self, Session: sessionmaker):
        """Create a new FileSetDAO.
        :param Session:
            The SQLAlchemy session to use."""
        self.Session = Session

    def add_file_set(self, file_set):
        """Add a FileSet to the database.
        :param file_set:
            The FileSet to add."""
        try:
            with self.Session() as session:
                session.add(file_set)
                session.commit()
        except Exception as e:
            print(f"Error adding FileSet to the database: {e}")

    def get_file_set_by_id(self, file_set_id):
        """Get a FileSet by its ID.
        :param file_set_id:
            The ID of the FileSet to get."""
        with self.Session() as session:
            return session.query(FileSet).get(file_set_id)

    def get_all_file_sets(self):
        """Get all FileSets.
        :return:
            A list of FileSets."""
        with self.Session() as session:
            return session.query(FileSet).all()
