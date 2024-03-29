import os
from typing import List
from model.file_model import FileModel
from sqlalchemy.orm import Mapped, mapped_column, relationship
from . import Base


class Job(Base):
    """A job to download files from an Archive.org page."""

    __tablename__ = "job"

    STATUS_CREATED = "Created"
    STATUS_RUNNING = "Running"
    STATUS_NOT_RUNNING = "Not Running"
    STATUS_COMPLETED = "Completed"
    STATUS_STOPPING = "Stopping"
    STATUS_STARTING = "Starting"

    RESUME_STARTING = "Resume Starting"
    RESUME_SUCCESS = "Resume Success"
    RESUME_FAILED = "Resume Failed"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(default=STATUS_CREATED)
    page_url: Mapped[str] = mapped_column(nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(default=0)
    target_folder: Mapped[str] = mapped_column(nullable=True)
    # cache field
    selected_files_with_known_size: Mapped[int] = mapped_column(default=0)
    # cache field
    selected_files_count: Mapped[int] = mapped_column(default=0)
    # cache field
    downloaded_bytes: Mapped[int] = mapped_column(default=0)
    # cache field
    files_done: Mapped[int] = mapped_column(default=0)
    threads_allocated: Mapped[int] = mapped_column(default=3)
    files: Mapped[List["FileModel"]] = relationship(back_populates="job",
                                                    cascade="all, delete, delete-orphan")

    def __len__(self) -> int:
        """Get the number of files in the job.
        :return: The number of files in the fileset"""
        return len(self.get_selected_filenames())

    def set_files(self, filemodels: list) -> None:
        """Set the filemodels in the fileset.
        :param filemodels:
            The filemodels to set"""
        self.files = filemodels

    def get_sorted_extensions(self) -> list:
        """Get the extensions of the files in the fileset, sorted alphabetically.
        :return: A list of extensions"""
        return sorted(set(filemodel.extension for filemodel in self.files))

    def get_sorted_filenames_by_extension(self, extension: str) -> list:
        """Get the filenames of the files in the fileset with the given extension, sorted
        alphabetically.
        :param extension:
            The extension to get the filenames for
        :return:
            A list of filenames"""
        if extension not in self.get_sorted_extensions():
            return []
        return sorted(
            filemodel.name
            for filemodel in self.files
            if filemodel.extension == extension
        )

    def set_file_selected(self, filename: str) -> None:
        """Set the file with the given filename to selected.
        :param filename:
            The filename to set to selected"""
        filemodel = next(
            (filemodel for filemodel in self.files if filemodel.name == filename), None
        )
        if filemodel:
            filemodel.selected = True

    def set_file_unselected(self, filename: str) -> None:
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
        return sorted(filemodel.name for filemodel in self.files if filemodel.selected)

    def get_selected_filemodels(self):
        """Get the filemodels of the selected files.
        :return:
            A list of filemodels"""
        return [filemodel for filemodel in self.files if filemodel.selected]

    def get_file_by_name(self, filename: str) -> FileModel:
        """Get the file with the given filename.
        :param filename:
            The filename to get the file for
        :return:
            The file with the given filename"""
        return next(
            (filemodel for filemodel in self.files if filemodel.name == filename), None
        )

    def add_file(self, file: FileModel) -> None:
        """Add a file to the job. Changes the file's local_path to the job's target_folder if
        the file does not have a local_path set.
        :param file:
            The file to add"""
        if file not in self.files:
            self.files.append(file)

    def get_selected_files_with_unknown_size(self) -> list:
        """Get the selected files with an unknown size.
        :return:
            A list of files"""
        return [file for file in self.files if file.selected and file.size_bytes == 0]

    def has_files_with_unknown_size(self) -> bool:
        """Determine whether the job has any files with an unknown size.
        :return:
            True if the job has files with an unknown size, False otherwise"""
        return len(self.get_selected_files_with_unknown_size()) > 0
