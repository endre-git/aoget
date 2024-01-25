import logging
import threading
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from aoget.model import FileModel, Job

logger = logging.getLogger(__name__)


class FileModelDAO:
    """Data access object for FileModels."""

    def __init__(self, session: Session, commit_lock: threading.Lock):
        """Create a new FileModelDAO.
        :param session:
            The SQLAlchemy session to use."""
        self.session = session
        self.commit_lock = commit_lock

    def _commit(self):
        """Thread-safe commit using the commit lock."""
        with self.commit_lock:
            self.session.commit()

    def create_file_model(self, job: Job, url: str, commit: bool = True) -> FileModel:
        """Create and persist a new FileModel using the bare minimum parameter set.
        :param job: The Job associated with the FileModel
        :param url: The URL of the file
        :param commit: Whether to commit the transaction
        :return: The newly created FileModel"""
        new_file_model = FileModel(url=url, job=job)
        try:
            self.session.add(new_file_model)
            if commit:
                self._commit()
            return new_file_model
        except SQLAlchemyError as e:
            logger.error(f"Error persisting newly created FileModel: {e}")
            raise e

    def add_file_model(self, file_model: FileModel, commit: bool = True) -> None:
        """Add a FileModel to the database.
        :param file_model: The FileModel to add
        :param commit: Whether to commit the transaction"""
        try:
            self.session.add(file_model)
            if commit:
                self._commit()
        except SQLAlchemyError as e:
            logger.error(f"Error adding FileModel to the database: {e}")
            raise e

    def get_file_model_by_id(self, file_model_id: int) -> FileModel:
        """Get a FileModel by its ID.
        :param file_model_id: The ID of the FileModel to get.
        :return: The requested FileModel object."""
        return self.session.query(FileModel).get(file_model_id)

    def get_all_file_models(self) -> list:
        """Get all FileModels.
        :return: A list of all FileModel objects."""
        return self.session.query(FileModel).all()

    def update_file_model_status(
        self, file_model_id: int, new_status: str, commit: bool = True
    ) -> None:
        """Update the status of a FileModel.
        :param file_model_id: The ID of the FileModel to update.
        :param new_status: The new status of the FileModel
        :param commit: Whether to commit the transaction"""
        with self.commit_lock:
            file_model = self.session.query(FileModel).get(file_model_id)
            if file_model:
                file_model.status = new_status
                if commit:
                    self.session.commit()

    def delete_file_model(self, file_model_id: int, commit: bool = True) -> None:
        """Delete a FileModel.
        :param file_model_id: The ID of the FileModel to delete
        :param commit: Whether to commit the transaction"""
        file_model = self.session.query(FileModel).get(file_model_id)
        if file_model:
            self.session.delete(file_model)
            if commit:
                self._commit()

    def delete_all_file_models(self, commit: bool = True) -> None:
        """Delete all FileModels.
        :param commit: Whether to commit the transaction"""
        self.session.query(FileModel).delete()
        if commit:
            self._commit()

    def update_file_model_size(
        self, file_model_id: int, new_size: int, commit: bool = True
    ) -> None:
        """Update the size of a FileModel.
        :param file_model_id: The ID of the FileModel to update
        :param new_size: The new size of the FileModel
        :param commit: Whether to commit the transaction"""
        file_model = self.session.query(FileModel).get(file_model_id)
        if file_model:
            file_model.size_bytes = new_size
            logger.info(f"Updated size of FileModel {file_model.name} to {new_size}")
            if commit:
                self._commit()

    def update_file_model_downloaded_bytes(
        self, file_model_id: int, new_downloaded_bytes: int, commit: bool = True
    ) -> None:
        """Update the number of downloaded bytes of a FileModel.
        :param file_model_id: The ID of the FileModel to update
        :param new_downloaded_bytes: The new number of downloaded bytes of the FileModel
        :param commit: Whether to commit the transaction"""
        file_model = self.session.query(FileModel).get(file_model_id)
        if file_model:
            file_model.downloaded_bytes = new_downloaded_bytes
            if commit:
                self._commit()
