import logging
from sqlalchemy.orm import Session
from model.dao.job_dao import JobDAO
from model.dao.file_model_dao import FileModelDAO
from model.dao.file_event_dao import FileEventDAO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from model import initialize_sql
from threading import RLock

logger = logging.getLogger(__name__)


class AogetDb:
    """App-level initializer and access to DB objects. AOGet uses a single, long-lived session for
    all DB operations. This is because the application is single-user, single-threaded and the
    session is not shared beetween threads, except for the state update thread that monitors file 
    downloads, but that is explicitly synchronized."""

    scoped_session_factory = None
    shared_session = None
    job_dao = None
    file_model_dao = None
    file_event_dao = None
    state_lock = RLock()


def init_db(connection_url: str):
    """Initialize the DB.
    :param session: The SQLAlchemy session to use."""
    engine = create_engine(connection_url)
    logger.info(f"Initializing DB engine using URL '{connection_url}'.")
    session_factory = sessionmaker(bind=engine)
    shared_session = session_factory()
    AogetDb.scoped_session_factory = scoped_session(sessionmaker(bind=engine))
    logger.info("Initialized DB session factory.")
    AogetDb.shared_session = shared_session
    logger.info("Initialized shared DB session.")
    AogetDb.job_dao = JobDAO(shared_session)
    AogetDb.file_model_dao = FileModelDAO(shared_session)
    AogetDb.file_event_dao = FileEventDAO(shared_session)
    initialize_sql(engine)
    logger.info("DB init completed.")
    return AogetDb


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
    return AogetDb.shared_session
