import logging
from model.dto.job_dto import JobDTO
from model.job import Job
from web.page_crawler import PageCrawler
from model.dto.file_model_dto import FileModelDTO

logger = logging.getLogger("JobEditorController")


class JobEditorController:
    """Controller for the Job Editor dialog"""

    def __init__(self, job_editor_dialog: any, main_window_controller: any):
        """Create a new JobEditorController."""
        self.job_editor_dialog = job_editor_dialog
        self.main_window_controller = main_window_controller
        self.job = None
        self.files_by_name = {}

    def build_fileset(self, page_url: str) -> list:
        """Fetch the links from the given page url."""
        urls_by_extension = PageCrawler(page_url).fetch_links()
        files_by_extension = {}
        for extension in urls_by_extension.keys():
            files_by_current_extension = []
            for url in urls_by_extension[extension]:
                file = FileModelDTO.from_url(url)
                files_by_current_extension.append(file)
                self.files_by_name[file.name] = file
            files_by_extension[extension] = sorted(files_by_current_extension)
        self.files_by_extension = files_by_extension
        return files_by_extension
 
    def set_file_selected(self, filename: str) -> None:
        """Set the file with the given filename to selected."""
        if filename not in self.files_by_name:
            raise ValueError(f"File with name {filename} not found.")
        file = self.files_by_name[filename]
        file.selected = True

    def set_file_unselected(self, filename: str) -> None:
        """Set the file with the given filename to unselected."""
        if filename not in self.files_by_name:
            raise ValueError(f"File with name {filename} not found.")
        file = self.files_by_name[filename]
        file.selected = False

    def __create_job(self, page_url):
        """Create a new job from the given page url."""
        job_name = page_url.split("/")[-1]
        self.job = JobDTO(
            id=-1,
            name=job_name,
            status=Job.STATUS_CREATED,
            page_url=page_url,
            total_size_bytes=0,
            target_folder=None,
        )

