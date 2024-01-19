"""A set of files, parsed from a page. Note that the underlying filemodels are mutable."""
from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship
from . import Base


class FileSet(Base):
    """A set of files, parsed from a page. Note that the underlying filemodels
    are mutable."""

    __tablename__ = "file_set"

    id = Column(Integer, primary_key=True)
    files = relationship("FileModel", back_populates="file_set")

    def __init__(self, filemodels=None):
        """Create a new FileSet.
        :param filemodels:
            The filemodels in the fileset."""
        self.files = filemodels or []

    def __len__(self) -> int:
        """Get the number of files in the fileset.
        :return: The number of files in the fileset"""
        return len(self.files.values())

    def set_files(self, filemodels: list) -> None:
        """Set the filemodels in the fileset.
        :param filemodels:
            The filemodels to set"""
        self.files = filemodels

    def get_sorted_extensions(self) -> list:
        """Get the extensions of the files in the fileset, sorted alphabetically.
        :return: A list of extensions"""
        sorted(set(filemodel.extension for filemodel in self.files))

    def get_sorted_filenames_by_extension(self, extension: str) -> list:
        """Get the filenames of the files in the fileset with the given extension, sorted
        alphabetically.
        :param extension:
            The extension to get the filenames for
        :return:
            A list of filenames"""
        if extension not in self.files_by_extension:
            return []
        return sorted(filemodel.name for filemodel in
                      self.files if filemodel.extension == extension)

    def set_selected(self, filename: str) -> None:
        """Set the file with the given filename to selected.
        :param filename:
            The filename to set to selected"""
        filemodel = next((filemodel for filemodel in self.files
                          if filemodel.name == filename), None)
        if filemodel:
            filemodel.selected = True

    def set_unselected(self, filename: str) -> None:
        """Set the file with the given filename to unselected.
        :param filename:
            The filename to set to unselected"""
        if filename not in self.files:
            return
        self.files[filename].selected = False

    def get_selected_filenames(self):
        """Get the filenames of the selected files sorted alphabetically.
        :return:
            A list of filenames"""
        return sorted(filemodel.name for filemodel in self.files
                      if filemodel.selected)
