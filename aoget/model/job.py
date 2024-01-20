import os
from model.file_model import FileModel
from sqlalchemy.orm import Mapped, mapped_column, relationship
from . import Base


class Job(Base):
    """A job to download files from an Archive.org page."""

    __tablename__ = "job"

    STATUS_CREATED = "Created"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(default=STATUS_CREATED)
    page_url: Mapped[str] = mapped_column(nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(default=0)
    target_folder: Mapped[str] = mapped_column(nullable=False)
    files = relationship("FileModel", back_populates="job")

    def __is_file_downloaded(self, file: FileModel) -> bool:
        """Determine whether the given file is downloaded.
        :param file:
            The file to check
        :return:
            True if the file is downloaded, False otherwise"""
        return os.path.isfile(os.path.join(self.job.target_folder, file.name))

    def __len__(self) -> int:
        """Get the number of files in the job.
        :return: The number of files in the fileset"""
        return len(self.get_selected_filenames())

    def ingest_links(self, ao_page) -> None:
        """Ingest the links from the ao_page into the job's fileset"""
        for extension, files in ao_page.files_by_extension.items():
            for url in files:
                self.files.append(FileModel(url))

    def resolve_files_to_download(self) -> list:
        """Resolve the files to download by comparing the files in the job's
        fileset with the files on disk.
            :return:
                A list of files to download"""
        files_to_download = []
        for filename in self.job.get_selected_filenames():
            file = self.job.file_set.files[filename]
            if not self.__is_file_downloaded(file):
                files_to_download.append(file)
        return files_to_download
    
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
        return sorted(filemodel.name for filemodel in
                      self.files if filemodel.extension == extension)

    def set_file_selected(self, filename: str) -> None:
        """Set the file with the given filename to selected.
        :param filename:
            The filename to set to selected"""
        filemodel = next((filemodel for filemodel in self.files
                          if filemodel.name == filename), None)
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
        return sorted(filemodel.name for filemodel in self.files
                      if filemodel.selected)

    def get_file_by_name(self, filename: str) -> FileModel:
        """Get the file with the given filename.
        :param filename:
            The filename to get the file for
        :return:
            The file with the given filename"""
        return next((filemodel for filemodel in self.files
                     if filemodel.name == filename), None)
