import logging
from collections import defaultdict
from model.dto.job_dto import JobDTO
from model.job import Job
from web.page_crawler import PageCrawler
from model.dto.file_model_dto import FileModelDTO
from model.file_model import FileModel
from view import JobEditorMode

logger = logging.getLogger("JobEditorController")


class JobEditorController:
    """Controller for the Job Editor dialog"""

    def __init__(
        self,
        job_editor_dialog: any,
        main_window_controller: any,
        mode: int
    ):
        """Create a new JobEditorController."""
        self.job_editor_dialog = job_editor_dialog
        self.app_controller = main_window_controller
        self.job = None
        self.files_by_name = {}
        self.files_by_extension = defaultdict(list)
        self.crawler = None
        self.page_url = ""
        self.mode = mode

    def build_fileset(self, page_url: str) -> list:
        """Fetch the links from the given page url."""
        self.page_url = page_url
        self.crawler = PageCrawler(page_url)
        urls_by_extension = self.crawler.fetch_links()
        files_by_extension = {}
        for extension in urls_by_extension.keys():
            files_by_current_extension = []
            for url in urls_by_extension[extension]:
                file = FileModelDTO.from_url(url)
                file.selected = False
                files_by_current_extension.append(file)
                self.files_by_name[file.name] = file
            files_by_extension[extension] = sorted(files_by_current_extension)
        self.files_by_extension = files_by_extension
        return files_by_extension

    def get_page_title(self) -> str:
        """Get the title of the page."""
        return self.crawler.ao_page.page_title

    def set_file_selected(self, filename: str) -> None:
        """Set the file with the given filename to selected."""
        if filename not in self.files_by_name:
            raise ValueError(f"File with name {filename} not found.")
        self.files_by_name[filename].selected = True

    def set_file_unselected(self, filename: str) -> None:
        """Set the file with the given filename to unselected."""
        if filename not in self.files_by_name:
            raise ValueError(f"File with name {filename} not found.")
        self.files_by_name[filename].selected = False

    def __create_job(self):
        """Create a new job from the given page url."""
        self.job = JobDTO(
            id=self.job.id if self.job else -1,
            name=self.job_editor_dialog.get_job_name(),
            status=self.job.status if self.job else Job.STATUS_CREATED,
            page_url=self.page_url,
            total_size_bytes=self.job.total_size_bytes if self.job else 0,
            target_folder=self.job_editor_dialog.get_target_folder(),
        )

    def use_files(self, files: list) -> None:
        """Use the given files instead of loading them from the DB. Used on the import path."""
        for file in files:
            self.files_by_name[file.name] = file
            self.files_by_extension[file.extension].append(file)

    def __load_files(self, job_id: int):
        """Load the files for the given job id. All, not just selected ones."""
        files = self.app_controller.get_file_dtos_by_job_id(job_id)
        self.files_by_extension = defaultdict(list)
        for file in files:
            self.files_by_name[file.name] = file
            self.files_by_extension[file.extension].append(file)

    def is_new_job(self):
        """Return True if the job is new, False otherwise. A job is
        considered new if it has no files or if all of its files has STATUS_NEW.
        For newly created and imported jobs, this is trivially True."""
        if self.mode in [JobEditorMode.JOB_NEW, JobEditorMode.JOB_IMPORTED]:
            return True
        for file in self.files_by_name.values():
            if file.status != FileModel.STATUS_NEW:
                return False
        return True

    def build_job(self):
        """Build a job from the given page url."""
        if self.mode == JobEditorMode.JOB_EDITED:
            self.update_job()
            return

        self.__create_job()
        job_id = self.app_controller.create_job_from_dto(self.job)
        # add all files to the job
        file_dtos = []
        for extension in self.files_by_extension.keys():
            for file in self.files_by_extension[extension]:
                file_dtos.append(file)
        self.app_controller.add_files_to_job(job_id, file_dtos)

    def update_job(self):
        """Update the job. This is used when the job is being edited"""
        self.__create_job()
        self.app_controller.update_job_from_dto(self.job)
        self.app_controller.update_selected_files(self.job.id, self.files_by_name)

    def load_job(self, job_name: str) -> JobDTO:
        """Load the given job."""
        self.job = self.app_controller.get_job_dto_by_name(job_name)
        self.page_url = self.job.page_url
        self.__load_files(self.job.id)
        return self.job
