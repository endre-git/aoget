import os
from model.file_set import FileSet
from model.file_model import FileModel


class Job:
    STATUS_CREATED = "Created"

    name = ""
    status = ""
    page_url = ""
    file_set = FileSet()
    post_processors = {}
    target_folder = ""

    def ingest_links(self, ao_page):
        """Ingest the links from the ao_page into the job's fileset"""
        filemodels = []
        for extension, files in ao_page.files_by_extension.items():
            for url in files:
                filemodels.append(FileModel(url))
        self.file_set.set_files(filemodels)

    def set_file_selected(self, filename):
        """Set the file with the given filename to selected"""
        self.file_set.set_selected(filename)

    def set_file_unselected(self, filename):
        """Set the file with the given filename to unselected"""
        self.file_set.set_unselected(filename)

    def get_selected_filenames(self):
        """Get the filenames of the selected files"""
        return self.file_set.get_selected_filenames()

    def __is_file_downloaded(self, file: FileModel) -> bool:
        """Determine whether the given file is downloaded.
        :param file:
            The file to check
        :return:
            True if the file is downloaded, False otherwise"""
        return os.path.isfile(os.path.join(self.job.target_folder, file.name))

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
