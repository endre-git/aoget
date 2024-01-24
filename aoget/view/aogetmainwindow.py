import logging
from typing import Any
from PyQt6.QtWidgets import (
    QMainWindow,
    QHeaderView,
    QTableWidgetItem,
    QProgressBar,
    QMessageBox,
)
from PyQt6 import uic

from view.newjobdialog import NewJobDialog
from util.aogetutil import human_timestamp_from, human_filesize
from aogetdb import get_job_dao, get_file_model_dao, get_file_event_dao
from web.background_resolver import BackgroundResolver, ResolverMonitor
from model.file_model import FileModel
from model.job_monitor import JobMonitor
from web.queued_downloader import QueuedDownloader
from web.monitor_daemon import MonitorDaemon

logger = logging.getLogger(__name__)


class AoGetMainWindow(QMainWindow):
    """Main window of the application. Note that this is more a controller than a view.
    View was done in Qt Designer and is loaded from a .ui file found under
    aoget/qt/main_window.ui"""

    def __init__(self):
        super(AoGetMainWindow, self).__init__()
        self.window_data = MainWindowData(self)
        uic.loadUi("aoget/qt/main_window.ui", self)
        self.__setup_ui()
        self.show()

    def __setup_ui(self):
        """Setup the UI"""
        # jobs table header
        self.__setup_jobs_table()
        self.__setup_files_table()

        self.__populate()

    def __setup_jobs_table(self):
        """Setup the jobs table and controls around it"""
        self.tblJobs.setColumnCount(6)
        self.tblJobs.setHorizontalHeaderLabels(
            ["Name", "Status", "File Count", "Progress", "Page URL", "Target Folder"]
        )
        header = self.tblJobs.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tblJobs.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        self.tblJobs.setSelectionMode(QHeaderView.SelectionMode.SingleSelection)
        # job control buttons
        self.btnCreateNew.clicked.connect(self.__on_create_new_job)

        # jobs table selection
        self.tblJobs.itemSelectionChanged.connect(self.__on_job_selected)
        self.tblJobs.doubleClicked.connect(self.__on_job_table_double_clicked)

    def __setup_files_table(self):
        """Setup the files table and controls around it"""
        self.tblFiles.setColumnCount(7)
        self.tblFiles.setHorizontalHeaderLabels(
            ["Name", "Status", "Size", "Progress", "URL", "Last Updated", "Last Event"]
        )
        header = self.tblFiles.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.tblFiles.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        self.tblFiles.setSelectionMode(QHeaderView.SelectionMode.SingleSelection)

        # jobs table selection
        # self.tblFiles.doubleClicked.connect(self.__on_file_table_double_clicked)

        # file toolbar buttons
        self.btnFileStartDownload.clicked.connect(self.__on_file_start_download)

    def __update_jobs_table(self):
        """Update the list of jobs"""
        self.tblJobs.setRowCount(self.window_data.job_count())

        for i, job in enumerate(self.window_data.get_jobs()):
            self.tblJobs.setItem(i, 0, QTableWidgetItem(job.name))
            self.tblJobs.setItem(i, 1, QTableWidgetItem(""))
            self.tblJobs.setItem(i, 2, QTableWidgetItem(""))
            self.tblJobs.setItem(i, 3, QTableWidgetItem(""))
            self.tblJobs.setItem(i, 4, QTableWidgetItem(job.page_url))
            self.tblJobs.setItem(i, 5, QTableWidgetItem(job.target_folder))

    def __on_job_selected(self):
        """A job has been selected in the jobs table"""
        self.__show_files(
            self.window_data.get_job_by_name(self.tblJobs.item(0, 0).text())
        )
        self.window_data.job_post_select(self.tblJobs.item(0, 0).text())

    def __on_job_table_double_clicked(self):
        """A job has been double clicked in the jobs table"""
        self.__show_files(self.jobs[self.tblJobs.item(0, 0).text()])

    def __on_create_new_job(self):
        """Create a new job"""
        dlg = NewJobDialog()
        val = dlg.exec()
        if val == 1:
            job = dlg.get_job()
            logger.info("New job created: %s", job.name)
            self.window_data.add_job(job)
            self.__update_jobs_table()
        else:
            logger.debug("New job creation cancelled")

    def __show_files(self, job):
        if job is None:
            return
        selected_filenames = job.get_selected_filenames()
        self.tblFiles.setRowCount(len(selected_filenames))
        for i, filename in enumerate(selected_filenames):
            file = job.get_file_by_name(filename)
            if file.has_history():
                latest_history_timestamp = file.get_latest_history_timestamp()
                latest_history_event = file.get_latest_history_entry().event
            self.tblFiles.setItem(i, 0, QTableWidgetItem(file.name))
            self.tblFiles.setItem(i, 1, QTableWidgetItem(file.status))
            self.tblFiles.setItem(
                i, 2, QTableWidgetItem(human_filesize(file.size_bytes))
            )
            progress_bar = QProgressBar(self.tblFiles)
            progress_bar.setValue(
                0
                if file.size_bytes == 0
                else int(file.downloaded_bytes / file.size_bytes * 100)
            )
            self.tblFiles.setCellWidget(i, 3, progress_bar)
            self.tblFiles.setItem(i, 4, QTableWidgetItem(file.url))
            self.tblFiles.setItem(
                i,
                5,
                QTableWidgetItem(
                    human_timestamp_from(latest_history_timestamp)
                    if latest_history_timestamp is not None
                    else ""
                ),
            )
            self.tblFiles.setItem(
                i,
                6,
                QTableWidgetItem(
                    latest_history_event if latest_history_event is not None else ""
                ),
            )

    def __populate(self):
        """Populate the UI with data from the database"""
        self.window_data.load_jobs()
        self.__update_jobs_table()

    def on_resolved_file_size(self, url, size):
        """Called when the file size of a remote file has been resolved"""
        if self.__is_job_selected():
            for row in range(self.tblFiles.rowCount()):
                file_url = self.tblFiles.item(row, 4).text()
                if url == file_url:
                    self.tblFiles.setItem(
                        row, 2, QTableWidgetItem(human_filesize(size))
                    )

    def __is_job_selected(self):
        """Determine whether a job is selected"""
        return (
            self.tblJobs.selectedItems() is not None
            and len(self.tblJobs.selectedItems()) > 0
        )

    def __is_file_selected(self):
        """Determine whether a file is selected"""
        return (
            self.tblFiles.selectedItems() is not None
            and len(self.tblFiles.selectedItems()) > 0
        )

    def __on_file_start_download(self):
        """Start downloading the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        ok, message = self.window_data.start_download(job_name, file_name)
        if ok:
            # update files table view to Downloading in the status column
            self.tblFiles.setItem(
                self.tblFiles.currentRow(), 1, QTableWidgetItem(message)
            )
        else:
            self.__show_error_dialog("Failed to start download: " + message)

    def __show_error_dialog(
        self, message, title="Error", icon=QMessageBox.Icon.Critical
    ):
        """Show an error dialog"""
        error_dialog = QMessageBox()
        error_dialog.setIcon(icon)
        error_dialog.setText(message)
        error_dialog.setWindowTitle(title)
        error_dialog.exec()

    def update_file_progress(self, jobname, filename, written, total):
        """Update the file progress of the given file if the right job is selected"""
        if (
            self.__is_job_selected()
            and jobname == self.tblJobs.selectedItems()[0].text()
        ):
            for row in range(self.tblFiles.rowCount()):
                if filename == self.tblFiles.item(row, 0).text():
                    progress_bar = self.tblFiles.cellWidget(row, 3)
                    progress_bar.setValue(int(written / total * 100))


class MainWindowJobMonitor(JobMonitor):
    """Implementation of the JobMonitor interface that publishes events to the main window"""

    def __init__(
        self, main_window_data: Any, main_window: AoGetMainWindow, job_name: str
    ):
        """Create a new job monitor."""
        self.main_window = main_window
        self.main_window_data = main_window_data
        self.job_name = job_name

    def on_download_progress_update(
        self, filename: str, written: int, total: int
    ) -> None:
        """When the download progress is updated.
        :param filename:
            The name of the file being downloaded
        :param written:
            Bytes written so far locally.
        :param total:
            Size of the remote file."""
        self.main_window.update_file_progress(self.job_name, filename, written, total)

    def on_file_status_update(self, filename: str, status: str) -> None:
        """When the status of a file is updated.
        :param filename:
            The name of the file
        :param status:
            The new status of the file"""
        logger.info("File status update: %s %s", filename, status)


class MainWindowData:
    """Data class for the main window"""

    jobs = {}
    active_resolvers = {}
    download_queues = {}
    download_monitors = {}

    def __init__(self, main_window: AoGetMainWindow):
        self.main_window = main_window
        self.monitor_daemon = MonitorDaemon()

    def load_jobs(self) -> None:
        """Load jobs from the database"""
        jobs = get_job_dao().get_all_jobs()
        for job in jobs:
            self.jobs[job.name] = job

    def job_count(self) -> int:
        """Get the number of jobs"""
        return len(self.jobs)

    def get_job_by_name(self, name) -> Any:
        """Get a job by its name"""
        return self.jobs[name] or None

    def get_jobs(self):
        """Get all jobs"""
        return self.jobs.values()

    def job_post_select(self, job_name: str) -> None:
        """Called after a job has been selected"""
        self.__resolve_file_sizes(job_name)

    def add_job(self, job) -> None:
        """Add a job"""
        self.jobs[job.name] = job
        get_job_dao().add_job(job)
        self.__resolve_file_sizes(job.name)

    def update_file_size(self, url, size):
        """Update the size of a file"""
        for job in self.jobs.values():
            for file in job.files:
                if file.url == url:
                    file.size_bytes = size
                    get_file_model_dao().update_file_model_size(file.id, size)

    def __resolve_file_sizes(self, job_name: str) -> None:
        """Resolve the file sizes of all selected files that have an unknown size"""
        if self.active_resolvers.get(job_name) is not None:
            logger.debug("Resolver for job %s is already running", job_name)
            return
        self.active_resolvers[job_name] = 'running'
        BackgroundResolver().resolve_file_sizes(
            job_name,
            self.jobs[job_name].get_selected_files_with_unknown_size(),
            ResolverMonitorImpl(self, self.main_window),
        )

    def on_resolver_finished(self, job_name: str) -> None:
        """Called when a resolver has finished"""
        self.active_resolvers.pop(job_name)

    def start_download(self, job_name: str, file_name: str) -> (bool, str):
        """Start downloading the given file
        :param job_name:
            The name of the job
        :param file_name:
            The name of the file
        :return:
            A tuple containing a boolean indicating whether the download was started successfully
            and a string containing the status of the file or the error message if download
            could not be started"""
        job = self.jobs[job_name]
        if self.download_queues.get(job_name) is None:
            self.__setup_downloader(job_name)

        self.download_queues[job_name].download_file(job.get_file_by_name(file_name))

        file = job.get_file_by_name(file_name)
        if file.status == FileModel.STATUS_DOWNLOADING:
            return False, "File is already downloading."
        file.status = FileModel.STATUS_DOWNLOADING
        get_file_model_dao().update_file_model_status(file.id, file.status)
        return True, FileModel.STATUS_DOWNLOADING

    def __setup_downloader(self, job_name: str) -> None:
        """Setup the downloader for the given job"""
        job = self.jobs[job_name]
        download_monitor = MainWindowJobMonitor(self, self.main_window, job_name)
        self.download_monitors[job_name] = download_monitor
        self.monitor_daemon.add_job_monitor(job_name, download_monitor)
        downloader = QueuedDownloader(job=job, monitor=self.monitor_daemon)
        self.download_queues[job_name] = downloader
        downloader.start()


class ResolverMonitorImpl(ResolverMonitor):
    """Implementation of the ResolverMonitor interface"""

    def __init__(
        self, main_window_data: MainWindowData, main_window: AoGetMainWindow
    ) -> None:
        self.main_window = main_window
        self.main_window_data = main_window_data

    def on_resolved_file_size(self, url, size):
        """Called when the file size of a remote file has been resolved"""
        self.main_window.on_resolved_file_size(url, size)
        self.main_window_data.update_file_size(url, size)

    def on_all_file_size_resolved(self, job_name):
        """Called when all file sizes have been resolved"""
        self.main_window_data.on_resolver_finished(job_name)
