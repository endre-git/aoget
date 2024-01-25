import logging
from PyQt6.QtWidgets import (
    QMainWindow,
    QHeaderView,
    QTableWidgetItem,
    QProgressBar,
    QMessageBox,
)
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, Qt
from .main_window_data import MainWindowData
from model.file_model import FileModel

from aoget.view.new_job_dialog import NewJobDialog
from util.aogetutil import human_timestamp_from, human_filesize, human_eta, human_rate

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window of the application. Note that this is more a controller than a view.
    View was done in Qt Designer and is loaded from a .ui file found under
    aoget/qt/main_window.ui"""

    PROGRESS_BAR_PASSIVE_STYLE = """
        QProgressBar {
            border: 1px solid grey;
            border-radius: 0px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #d0d6db;
            width: 1px;
        }"""

    PROGRESS_BAR_ACTIVE_STYLE = """
        QProgressBar {
            border: 1px solid grey;
            border-radius: 0px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #31a7f5;
            width: 1px;
        }"""

    FILE_NAME_IDX = 0
    FILE_SIZE_IDX = 1
    FILE_STATUS_IDX = 2
    FILE_PROGRESS_IDX = 3
    FILE_RATE_IDX = 4
    FILE_ETA_IDX = 5
    FILE_LAST_UPDATED_IDX = 6
    FILE_LAST_EVENT_IDX = 7

    update_file_progress_signal = pyqtSignal(str, str, int, int, int)
    update_file_status_signal = pyqtSignal(str, str, str, str, str)
    resolved_file_size_signal = pyqtSignal(str, str, int)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.window_data = MainWindowData(self)
        uic.loadUi("aoget/qt/main_window.ui", self)
        self.__setup_ui()
        self.show()

    def __setup_ui(self):
        """Setup the UI"""

        # connect signals
        self.update_file_progress_signal.connect(self.update_file_progress)
        self.update_file_status_signal.connect(self.update_file_status)
        self.resolved_file_size_signal.connect(self.on_resolved_file_size)

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
        column_widths = [200, 100, 100, 100, 200, 200]
        for i, width in enumerate(column_widths):
            self.tblJobs.setColumnWidth(i, width)

        # job control buttons
        self.btnCreateNew.clicked.connect(self.__on_create_new_job)

        # jobs table selection
        self.tblJobs.itemSelectionChanged.connect(self.__on_job_selected)
        self.tblJobs.doubleClicked.connect(self.__on_job_table_double_clicked)

    def __setup_files_table(self):
        """Setup the files table and controls around it"""
        self.tblFiles.setColumnCount(
            8
        )  # Increase column count to accommodate the new "Rate" column
        self.tblFiles.setHorizontalHeaderLabels(
            [
                "Name",
                "Size",
                "Status",
                "Progress",
                "Rate",
                "ETA",
                "Last Updated",
                "Last Event",
            ]
        )
        header = self.tblFiles.horizontalHeader()
        header.setSectionResizeMode(
            MainWindow.FILE_NAME_IDX, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            MainWindow.FILE_SIZE_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.FILE_STATUS_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.FILE_PROGRESS_IDX, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            MainWindow.FILE_RATE_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.FILE_ETA_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.FILE_LAST_UPDATED_IDX,
            QHeaderView.ResizeMode.Fixed,
        )
        header.setSectionResizeMode(
            MainWindow.FILE_LAST_EVENT_IDX, QHeaderView.ResizeMode.Stretch
        )
        self.tblFiles.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        self.tblFiles.setSelectionMode(QHeaderView.SelectionMode.SingleSelection)
        column_widths = [200, 70, 100, 300, 70, 100, 150, 300]
        for i, width in enumerate(column_widths):
            self.tblFiles.setColumnWidth(i, width)

        # Make columns sortable
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.__sort_files_table)

        # jobs table selection
        # self.tblFiles.doubleClicked.connect(self.__on_file_table_double_clicked)

        # file toolbar buttons
        self.btnFileStartDownload.clicked.connect(self.__on_file_start_download)
        self.btnFileStopDownload.clicked.connect(self.__on_file_stop_download)

    def __sort_files_table(self, logical_index):
        """Sort the files table by the given column"""
        self.tblFiles.sortItems(logical_index)

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
            # ["Name", "Size", "Status", "Progress", "Rate", "ETA", "URL", "Last Updated", "Last Event"]
            self.tblFiles.setItem(
                i, MainWindow.FILE_NAME_IDX, QTableWidgetItem(file.name)
            )
            self.tblFiles.setItem(
                i,
                MainWindow.FILE_SIZE_IDX,
                QTableWidgetItem(human_filesize(file.size_bytes)),
            )
            self.tblFiles.setItem(
                i, MainWindow.FILE_STATUS_IDX, QTableWidgetItem(file.status)
            )
            progress_bar = QProgressBar(self.tblFiles)
            progress_bar.setValue(
                0
                if file.size_bytes == 0
                else int(file.downloaded_bytes / file.size_bytes * 100)
            )
            progress_bar.setStyleSheet(MainWindow.PROGRESS_BAR_PASSIVE_STYLE)
            self.tblFiles.setCellWidget(i, MainWindow.FILE_PROGRESS_IDX, progress_bar)
            self.tblFiles.setItem(
                i,
                MainWindow.FILE_LAST_UPDATED_IDX,
                QTableWidgetItem(
                    human_timestamp_from(latest_history_timestamp)
                    if latest_history_timestamp is not None
                    else ""
                ),
            )
            self.tblFiles.setItem(
                i,
                MainWindow.FILE_LAST_EVENT_IDX,
                QTableWidgetItem(
                    latest_history_event if latest_history_event is not None else ""
                ),
            )

    def __populate(self):
        """Populate the UI with data from the database"""
        self.window_data.load_jobs()
        self.__update_jobs_table()

    def on_resolved_file_size(self, job_name, file_name, size):
        """Called when the file size of a remote file has been resolved"""
        if (
            self.__is_job_selected()
            and job_name == self.tblJobs.selectedItems()[0].text()
        ):
            for row in range(self.tblFiles.rowCount()):
                file_in_table = self.tblFiles.item(row, MainWindow.FILE_NAME_IDX).text()
                if file_name == file_in_table:
                    self.tblFiles.setItem(
                        row,
                        MainWindow.FILE_SIZE_IDX,
                        QTableWidgetItem(human_filesize(size)),
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
                self.tblFiles.currentRow(),
                MainWindow.FILE_STATUS_IDX,
                QTableWidgetItem(message),
            )
        else:
            self.__show_error_dialog("Failed to start download: " + message)

    def __on_file_stop_download(self):
        """Stop downloading the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        ok, message = self.window_data.stop_download(job_name, file_name)
        if ok:
            # update files table view to Downloading in the status column
            self.tblFiles.setItem(
                self.tblFiles.currentRow(),
                MainWindow.FILE_STATUS_IDX,
                QTableWidgetItem(message),
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

    def __restyleFileProgressBar(self, row, style):
        """Disable the given cell in the files table"""
        progress_bar = self.tblFiles.cellWidget(row, MainWindow.FILE_PROGRESS_IDX)
        progress_bar.setStyleSheet(style)

    def update_file_progress(
        self, jobname, filename, percent_completed, download_rate, eta_seconds
    ):
        """Update the file progress of the given file if the right job is selected"""
        if (
            self.__is_job_selected()
            and jobname == self.tblJobs.selectedItems()[0].text()
        ):
            for row in range(self.tblFiles.rowCount()):
                if filename == self.tblFiles.item(row, MainWindow.FILE_NAME_IDX).text():
                    progress_bar = self.tblFiles.cellWidget(
                        row, MainWindow.FILE_PROGRESS_IDX
                    )
                    progress_bar.setValue(percent_completed)

                    if (
                        self.tblFiles.item(row, MainWindow.FILE_STATUS_IDX).text()
                        == FileModel.STATUS_DOWNLOADING
                    ):
                        self.tblFiles.setItem(
                            row,
                            MainWindow.FILE_RATE_IDX,
                            QTableWidgetItem(human_rate(download_rate)),
                        )
                        self.tblFiles.setItem(
                            row,
                            MainWindow.FILE_ETA_IDX,
                            QTableWidgetItem(human_eta(eta_seconds)),
                        )
                    else:
                        self.tblFiles.setItem(
                            row,
                            MainWindow.FILE_RATE_IDX,
                            QTableWidgetItem(""),
                        )
                        self.tblFiles.setItem(
                            row,
                            MainWindow.FILE_ETA_IDX,
                            QTableWidgetItem(""),
                        )
                    return

    def update_file_status(self, jobname, filename, status, last_updated, last_event):
        """Update the file status of the given file if the right job is selected"""
        if (
            self.__is_job_selected()
            and jobname == self.tblJobs.selectedItems()[0].text()
        ):
            for row in range(self.tblFiles.rowCount()):
                if filename == self.tblFiles.item(row, MainWindow.FILE_NAME_IDX).text():
                    self.tblFiles.item(row, MainWindow.FILE_STATUS_IDX).setText(status)
                    self.tblFiles.setItem(
                        row,
                        MainWindow.FILE_LAST_UPDATED_IDX,
                        QTableWidgetItem(human_timestamp_from(last_updated)),
                    )
                    self.tblFiles.setItem(
                        row,
                        MainWindow.FILE_LAST_EVENT_IDX,
                        QTableWidgetItem(last_event),
                    )
                    if status != FileModel.STATUS_DOWNLOADING:
                        self.tblFiles.item(row, MainWindow.FILE_RATE_IDX).setText("")
                        self.tblFiles.item(row, MainWindow.FILE_ETA_IDX).setText("")
                        self.__restyleFileProgressBar(
                            row, MainWindow.PROGRESS_BAR_PASSIVE_STYLE
                        )
                    else:
                        self.__restyleFileProgressBar(
                            row, MainWindow.PROGRESS_BAR_ACTIVE_STYLE
                        )
                    return
