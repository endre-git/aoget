"""Transactional commits used by concurrent threads to update the database."""

import logging
from aoget.model.file_model import FileModel
from aoget.model.job import Job
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def update_file_model_status(
    session_factory: Session, job_name: str, file_name: str, new_status: str
) -> None:
    """Update the status of a FileModel.
    :param job_name: The name of the job to update
    :param file_name: The name of the file to update
    :param new_status: The new status of the FileModel"""
    with session_factory() as session:
        job_model = session.query(Job).filter_by(name=job_name).first()
        if job_model:
            file_model = (
                session.query(FileModel)
                .filter_by(job_id=job_model.id, name=file_name)
                .first()
            )
            if file_model:
                file_model.status = new_status
                session.commit()
                logger.info(
                    f"Updated status of FileModel {file_model.name} to {new_status}"
                )
            else:
                logger.error(f"Could not find FileModel {file_name} in job {job_name}")
        else:
            logger.error(f"Could not find job {job_name}")


def update_file_model_size(
    session_factory: Session, job_name: str, file_name: str, new_size: int
) -> None:
    """Update the size of a FileModel.
    :param job_name: The name of the job to update
    :param file_name: The name of the file to update
    :param new_size: The new size of the FileModel"""
    with session_factory() as session:
        job_model = session.query(Job).filter_by(name=job_name).first()
        if job_model:
            file_model = (
                session.query(FileModel)
                .filter_by(job_id=job_model.id, name=file_name)
                .first()
            )
            if file_model:
                file_model.size_bytes = new_size
                session.commit()
                logger.info(
                    f"Updated size of FileModel {file_model.name} to {new_size}"
                )
            else:
                logger.error(f"Could not find FileModel {file_name} in job {job_name}")
        else:
            logger.error(f"Could not find job {job_name}")


def update_file_model_downloaded_bytes(
    session_factory: any, job_name: str, file_name: str, new_downloaded_bytes: int
) -> None:
    """Update the downloaded bytes of a FileModel.
    :param job_name: The name of the job to update
    :param file_name: The name of the file to update
    :param new_downloaded_bytes: The new downloaded bytes of the FileModel"""
    with session_factory() as session:
        job_model = session.query(Job).filter_by(name=job_name).first()
        if job_model:
            file_model = (
                session.query(FileModel)
                .filter_by(job_id=job_model.id, name=file_name)
                .first()
            )
            if file_model:
                file_model.downloaded_bytes = new_downloaded_bytes
                session.commit()
                logger.info(
                    f"Updated downloaded bytes of FileModel {file_model.name} to {new_downloaded_bytes}"
                )
            else:
                logger.error(f"Could not find FileModel {file_name} in job {job_name}")
        else:
            logger.error(f"Could not find job {job_name}")
