"""A set of files, parsed from a page. Note that the underlying filemodels are mutable."""
from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from . import Base


class FileSet(Base):
    """A set of files, parsed from a page. Note that the underlying filemodels
    are mutable."""

    __tablename__ = "file_set"



    def __init__(self, filemodels=None):
        """Create a new FileSet.
        :param filemodels:
            The filemodels in the fileset."""
        self.files = filemodels or []

