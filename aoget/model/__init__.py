from threading import current_thread, RLock
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase

global DBSession


class Base(DeclarativeBase):
    pass


from .file_event import FileEvent
from .file_model import FileModel
from .job import Job


def initialize_sql(engine):
    global DBSession
    DBSession = scoped_session(sessionmaker(bind=engine))
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
