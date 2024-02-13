from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase

global DBSession


class Base(DeclarativeBase):
    pass


from .file_event import FileEvent  # noqa: F401, E402
from .file_model import FileModel  # noqa: F401, E402
from .job import Job  # noqa: F401, E402


def initialize_sql(engine):
    global DBSession
    DBSession = scoped_session(sessionmaker(bind=engine))
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
