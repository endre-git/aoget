import logging
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase
from sqlalchemy.engine import Engine
from sqlalchemy import event

global DBSession

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


from .file_event import FileEvent  # noqa: F401, E402
from .file_model import FileModel  # noqa: F401, E402
from .job import Job  # noqa: F401, E402


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    logger.info("Setting SQLite foreign key enforcement.")
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def initialize_sql(engine):
    logger.info("Initializing DB.")
    global DBSession
    DBSession = scoped_session(sessionmaker(bind=engine))
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
