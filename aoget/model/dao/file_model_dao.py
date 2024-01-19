import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from aoget.model import FileModel

logger = logging.getLogger(__name__)


class FileModelDAO:
    """Data access object for FileModels."""

    def __init__(self, Session: sessionmaker):
        """Create a new FileModelDAO.
        :param Session:
            The SQLAlchemy session to use."""
        self.Session = Session

    def add_file_model(self, file_model: FileModel) -> None:
        """Add a FileModel to the database.
        :param file_model:
            The FileModel to add."""
        try:
            with self.Session() as session:
                session.add(file_model)
                session.commit()
        except SQLAlchemyError as e:
            print(f"Error adding FileModel to the database: {e}")
            logger.error(f"Error adding FileModel to the database: {e}")

    def get_file_model_by_id(self, file_model_id: int) -> FileModel:
        """Get a FileModel by its ID.
        :param file_model_id:
            The ID of the FileModel to get."""
        with self.Session() as session:
            return session.query(FileModel).get(file_model_id)

    def get_all_file_models(self) -> list:
        """Get all FileModels.
        :return:
            A list of FileModels."""
        with self.Session() as session:
            return session.query(FileModel).all()

    def update_file_model_status(self, file_model_id: int, new_status: str) -> None:
        """Update the status of a FileModel.
        :param file_model_id:
            The ID of the FileModel to update.
        :param new_status:
            The new status of the FileModel."""
        with self.Session() as session:
            file_model = session.query(FileModel).get(file_model_id)
            if file_model:
                file_model.status = new_status
                session.commit()

    def delete_file_model(self, file_model_id: int) -> None:
        """Delete a FileModel.
        :param file_model_id:
            The ID of the FileModel to delete."""
        with self.Session() as session:
            file_model = session.query(FileModel).get(file_model_id)
            if file_model:
                session.delete(file_model)
                session.commit()

    def delete_all_file_models(self) -> None:
        """Delete all FileModels."""
        with self.Session() as session:
            session.query(FileModel).delete()
            session.commit()
