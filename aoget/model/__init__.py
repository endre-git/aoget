from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase

DBSession = scoped_session(sessionmaker())


class Base(DeclarativeBase):
    pass

from .file_model import FileModel
from .file_event import FileEvent


def initialize_sql(engine):
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
