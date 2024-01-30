import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from aoget.model import FileModel, Job
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)


class FileModelDAO:
    """Data access object for FileModels."""

    def __init__(self, shared_session: Session):
        """Create a new FileModelDAO.
        :param session:
            The SQLAlchemy session to use."""
        self.session = shared_session

    def _commit(self):
        """Commit the current transaction."""
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error committing transaction: {e}")
            raise e

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
        file_model = self.session.query(FileModel).get(file_model_id)
        if file_model:
            file_model.status = new_status
            if commit:
                self._commit()

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

    def get_selected_files_of_job(self, job_id: int) -> list:
        """Get the selected files of a job.
        :param job_id: The ID of the job to get the selected files for
        :return: A list of FileModel objects"""
        return (
            self.session.query(FileModel).filter_by(job_id=job_id, selected=True).all()
        )

    def get_selected_files_with_unknown_size(self, job_id: int) -> list:
        """Get the selected files of a job with unknown size.
        :param job_id: The ID of the job to get the selected files for
        :return: A list of FileModel objects"""
        return (
            self.session.query(FileModel)
            .filter_by(job_id=job_id, selected=True)
            .filter(FileModel.size_bytes.in_([None, -1]))
            .all()
        )

    def get_file_model_by_name(self, job_id: int, filename: str) -> FileModel:
        """Get a FileModel by its name.
        :param job_id: The ID of the job to get the FileModel for
        :param filename: The name of the FileModel to get
        :return: The requested FileModel"""
        return (
            self.session.query(FileModel)
            .filter_by(job_id=job_id, name=filename)
            .first()
        )
