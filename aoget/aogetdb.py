import logging
from sqlalchemy.orm import Session
from aoget.model.dao.job_dao import JobDAO
from aoget.model.dao.file_model_dao import FileModelDAO
from aoget.model.dao.file_event_dao import FileEventDAO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aoget.model import initialize_sql

logger = logging.getLogger(__name__)


class AogetDb:
    """App-level initializer and access to DB objects. AOGet uses a single, long-lived session for
    all DB operations. This is because the application is single-user, single-threaded and the
    session is not shared beetween threads, except for the state update thread that monitors file 
    downloads, but that is explicitly synchronized."""

    session = None
    job_dao = None
    file_model_dao = None
    file_event_dao = None


def init_db(connection_url: str) -> AogetDb:
    """Initialize the DB.
    :param session: The SQLAlchemy session to use.
    :return: The AogetDb instance."""
    engine = create_engine(connection_url)
    logger.info(f"Initializing DB engine using URL '{connection_url}'.")
    Session = sessionmaker(bind=engine)
    session = Session()
    AogetDb.session = session
    AogetDb.job_dao = JobDAO(session)
    AogetDb.file_model_dao = FileModelDAO(session)
    AogetDb.file_event_dao = FileEventDAO(session)
    initialize_sql(engine)
    logger.info("Initialized DB.")


def get_job_dao() -> JobDAO:
    """Get the JobDAO instance.
    :return: The JobDAO instance."""
    return AogetDb.job_dao


def get_file_model_dao() -> FileModelDAO:
    """Get the FileModelDAO instance.
    :return: The FileModelDAO instance."""
    return AogetDb.file_model_dao


def get_file_event_dao() -> FileEventDAO:
    """Get the FileEventDAO instance.
    :return: The FileEventDAO instance."""
    return AogetDb.file_event_dao


def get_session() -> Session:
    """Get the SQLAlchemy session.
    :return: The SQLAlchemy session."""
    return AogetDb.session
