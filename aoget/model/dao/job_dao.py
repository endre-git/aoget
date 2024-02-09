from typing import List
from sqlalchemy.orm import Session
from ..job import Job

import logging

logger = logging.getLogger(__name__)


class JobDAO:
    """Data access object for Jobs. Uses a shared session object. Mutators by default commit the 
    changes."""

    def __init__(self, session: Session):
        """Create a new JobDAO.
        :param Session:
            The SQLAlchemy session to use."""
        self.session = session

    def create_job(self, name: str, page_url: str, target_folder: str, commit: bool = True) -> Job:
        """Create a new Job using the bare minimum parameter set.
        :param name:
            The name of the job
        :param page_url:
            The URL of the Archive.org page
        :param target_folder:
            The target folder to download files to
        :param commit:
            Whether to commit the changes to the database
        :return:
            The newly created Job"""
        new_job = Job(name=name, page_url=page_url, target_folder=target_folder)
        self.session.add(new_job)
        if commit:
            self.session.commit()
            logger.info(f"Created and committed new job: {new_job}")
        else:
            logger.info(f"Created new job (not committed): {new_job}")
        return new_job

    def add_job(self, job: Job, commit: bool = True) -> None:
        """Add a Job to the database.
        :param job:
            The Job to add
        :param commit:
            Whether to commit the changes to the database"""
        self.session.add(job)
        if commit:
            self.session.commit()
            logger.info(f"Added and committed job: {job}")
        else:
            logger.info(f"Added job (not committed): {job}")

    def get_job_by_id(self, job_id: int) -> Job:
        """Get a Job by its ID.
            :param job_id:
            The ID of the Job to get
            :return:
                The Job"""
        return self.session.query(Job).filter(Job.id == job_id).first()

    def get_all_jobs(self) -> List[Job]:
        """Get all Jobs.
        :return:
            A list of Jobs"""
        return self.session.query(Job).all()

    def delete_job_by_id(self, job_id: int, commit: bool = True) -> None:
        """Delete a Job by its ID.
        :param job_id:
            The ID of the Job to delete
        :param commit:
            Whether to commit the changes to the database"""
        job = self.session.query(Job).filter_by(id=job_id).first()
        if job is not None:
            self.session.delete(job)
            if commit:
                self.session.commit()
                logger.info(f"Deleted and committed job: {job}")
            else:
                logger.info(f"Deleted job (not committed): {job}")
        else:
            logger.info(f"Job with ID {job_id} not found, deleted nothing.")

    def delete_all_jobs(self, commit: bool = True) -> None:
        """Delete all Jobs.
        :param commit:
            Whether to commit the changes to the database"""
        self.session.query(Job).delete()
        if commit:
            self.session.commit()
            logger.info("Deleted all jobs and committed.")
        else:
            logger.info("Deleted all jobs (not committed).")

    def delete_job(self, job: Job, commit: bool = True) -> None:
        """Delete a Job.
        :param job:
            The Job to delete
        :param commit:
            Whether to commit the changes to the database"""
        self.session.delete(job)
        if commit:
            self.session.commit()
            logger.info(f"Deleted and committed job: {job}")
        else:
            logger.info(f"Deleted job (not committed): {job}")

    def get_job_by_name(self, name: str) -> Job:
        """Get a Job by its name.
        :param name:
            The name of the Job to get
        :return:
            The Job"""
        return self.session.query(Job).filter(Job.name == name).first()

    def save_job(self, job: Job, commit: bool = True) -> None:
        """Save a Job.
        :param job:
            The Job to save
        :param commit:
            Whether to commit the changes to the database"""
        if commit:
            self.session.commit()
