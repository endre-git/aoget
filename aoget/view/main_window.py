import os
import time
import logging
from PyQt6.QtWidgets import (
    QMainWindow,
    QHeaderView,
    QTableWidgetItem,
    QProgressBar,
    QMessageBox,
    QApplication,
)
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from controller.main_window_controller import MainWindowController

from view.job_editor_dialog import JobEditorDialog
from view.file_details_dialog import FileDetailsDialog
from util.aogetutil import human_timestamp_from, human_filesize, human_eta, human_rate
from util.qt_util import confirmation_dialog
from model.file_model import FileModel
from db.aogetdb import AogetDb

from model.job import Job
from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO

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

    JOB_NAME_IDX = 0
    JOB_SIZE_IDX = 1
    JOB_STATUS_IDX = 2
    JOB_RATE_IDX = 3
    JOB_THREADS_IDX = 4
    JOB_FILES_IDX = 5
    JOB_PROGRESS_IDX = 6
    JOB_ETA_IDX = 7
    JOB_TARGET_FOLDER_IDX = 8

    update_job_signal = pyqtSignal(JobDTO)
    update_file_signal = pyqtSignal(FileModelDTO)

    def __init__(self, aoget_db: AogetDb):
        super(MainWindow, self).__init__()
        self.controller = MainWindowController(self, aoget_db)
        uic.loadUi("aoget/qt/main_window.ui", self)
        self.__setup_ui()
        self.show()
        self.controller.resume_state()

    def __setup_ui(self):
        """Setup the UI"""

        # connect signals
        self.update_job_signal.connect(self.update_job)
        self.update_file_signal.connect(self.update_file)

        # jobs table header
        self.__setup_jobs_table()
        self.__setup_files_table()
        self.__populate()

    def __setup_jobs_table(self):
        """Setup the jobs table and controls around it"""

        labels = [
            "Name",
            "Size",
            "Status",
            "Rate",
            "Threads",
            "Files",
            "Progress",
            "ETA",
            "Target Folder",
        ]
        self.tblJobs.setColumnCount(len(labels))
        self.tblJobs.setHorizontalHeaderLabels(labels)
        header = self.tblJobs.horizontalHeader()
        header.setSectionResizeMode(
            MainWindow.JOB_NAME_IDX, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            MainWindow.JOB_SIZE_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.JOB_STATUS_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.JOB_RATE_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.JOB_THREADS_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.JOB_FILES_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.JOB_PROGRESS_IDX, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            MainWindow.JOB_TARGET_FOLDER_IDX, QHeaderView.ResizeMode.Stretch
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_NAME_IDX).setToolTip(
            "Name of the job"
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_SIZE_IDX).setToolTip(
            "Total size of the job, calculated from file sizes. If still being resolved, will be shown as >X."
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_STATUS_IDX).setToolTip(
            "Status of the job"
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_RATE_IDX).setToolTip(
            "Download rate of the job"
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_THREADS_IDX).setToolTip(
            "Number of active download threads / allocated download threads"
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_FILES_IDX).setToolTip(
            "Number of downloaded files / total files in the job"
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_PROGRESS_IDX).setToolTip(
            "Progress of the job based on size, not shown if the size is not fully resolved."
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_ETA_IDX).setToolTip(
            "ETA for the job to complete. Not shown if the size is not fully resolved. Might be way off with poor server bandwidth."
        )
        self.tblJobs.horizontalHeaderItem(MainWindow.JOB_TARGET_FOLDER_IDX).setToolTip(
            "Target folder for the job, where the downloaded files are saved."
        )

        self.tblJobs.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        self.tblJobs.setSelectionMode(QHeaderView.SelectionMode.SingleSelection)
        column_widths = [200, 70, 100, 70, 70, 70, 250, 70, 200]
        for i, width in enumerate(column_widths):
            self.tblJobs.setColumnWidth(i, width)

        # job control buttons
        self.btnJobCreate.clicked.connect(self.__on_create_new_job)
        self.btnJobEdit.clicked.connect(self.__on_edit_job)
        self.btnJobRemoveFromList.clicked.connect(self.__on_job_remove_from_list)
        self.btnJobRemove.clicked.connect(self.__on_job_remove_from_disk)

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
        self.tblFiles.clicked.connect(self.__on_file_selected)

        # file toolbar buttons
        self.btnFileStartDownload.clicked.connect(self.__on_file_start_download)
        self.btnFileStopDownload.clicked.connect(self.__on_file_stop_download)
        self.btnFileRedownload.clicked.connect(self.__on_file_redownload)
        self.btnFileRemoveFromList.clicked.connect(self.__on_file_remove_from_list)
        self.btnFileRemove.clicked.connect(self.__on_file_remove)
        self.btnFileDetails.clicked.connect(self.__on_file_details)
        self.btnFileShowInFolder.clicked.connect(self.__on_file_show_in_folder)
        self.btnFileCopyURL.clicked.connect(self.__on_file_copy_url)
        self.btnFileOpenLink.clicked.connect(self.__on_file_open_link)

        # disable all file toolbar buttons
        self.btnFileStartDownload.setEnabled(False)
        self.btnFileStopDownload.setEnabled(False)
        self.btnFileRedownload.setEnabled(False)
        self.btnFileRemoveFromList.setEnabled(False)
        self.btnFileRemove.setEnabled(False)
        self.btnFileDetails.setEnabled(False)
        self.btnFileShowInFolder.setEnabled(False)
        self.btnFileCopyURL.setEnabled(False)
        self.btnFileOpenLink.setEnabled(False)

    def __populate(self):
        """Populate the UI with data from the database"""
        self.__update_jobs_table()

    def __sort_files_table(self, logical_index):
        """Sort the files table by the given column"""
        self.tblFiles.sortItems(logical_index)

    def __update_jobs_table(self):
        """Update the list of jobs"""
        jobs = self.controller.get_job_dtos()
        self.tblJobs.setRowCount(len(jobs))

        for i, job in enumerate(jobs):
            self.__set_job_at_row(i, job)

    def __on_job_selected(self):
        """A job has been selected in the jobs table"""
        if not self.__is_job_selected():
            return
        selected_job_name = self.tblJobs.selectedItems()[0].text()
        self.__show_files(selected_job_name)
        self.controller.job_post_select(selected_job_name)

    def __on_job_table_double_clicked(self):
        """A job has been double clicked in the jobs table"""
        pass

    def __on_create_new_job(self):
        """Create a new job"""
        selected_job_name = (
            self.tblJobs.selectedItems()[0].text() if self.__is_job_selected() else None
        )
        dlg = JobEditorDialog(self.controller)
        val = dlg.exec()
        if val == 1:
            self.__update_jobs_table()
            newly_selected_job = (
                self.tblJobs.selectedItems()[0].text()
                if self.__is_job_selected()
                else None
            )
            if (
                newly_selected_job is not None
                and newly_selected_job != selected_job_name
            ):
                self.__show_files(newly_selected_job)
                self.controller.job_post_select(newly_selected_job)

    def __on_edit_job(self):
        """Edit the selected job"""
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        if self.controller.is_job_downloading(job_name):
            self.__show_error_dialog(
                "Job is running. Please stop all downloads before editing."
            )
            return
        dlg = JobEditorDialog(self.controller, job_name)
        val = dlg.exec()
        if val == 1:
            self.__show_files(job_name)

    def __on_job_remove_from_list(self):
        """Remove the selected job from the list"""
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        if confirmation_dialog(
            self,
            f"""Remove job: <b>{job_name}</b>?
            <p>Running downloads will be stopped.<br>
            Files will not be deleted.</p>""",
        ):
            self.controller.delete_job(job_name)
            self.__update_jobs_table()
            # deselect table
            self.tblJobs.clearSelection()
            self.__show_files(None)

    def __on_job_remove_from_disk(self):
        """Remove the selected job from the list and delete the local files"""
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        if confirmation_dialog(
            self,
            f"""Remove job and delete the corresponding files: <b>{job_name}</b>?
            <p>Running downloads will be stopped.<br>
            Files <b>will</b> be deleted.</p>""",
        ):
            self.controller.delete_job(job_name, delete_from_disk=True)
            self.__update_jobs_table()

    def __show_files(self, job_name):
        """Show the files of the given job in the files table."""
        if job_name is None:
            for i in range(0, self.tblFiles.rowCount()):
                self.tblFiles.setRowHidden(i, True)
            return
        selected_files = self.controller.get_selected_file_dtos(job_name)
        self.tblFiles.setRowCount(self.controller.get_largest_fileset_length())
        for i, file in enumerate(selected_files):
            self.__set_file_at_row(i, file)
            self.tblFiles.setRowHidden(i, False)
        for i in range(len(selected_files), self.tblFiles.rowCount()):
            self.tblFiles.setRowHidden(i, True)

    def __is_job_selected(self):
        """Determine whether a job is selected"""
        return (
            self.tblJobs.selectedItems() is not None
            and len(self.tblJobs.selectedItems()) > 0
        )

    def __on_file_selected(self):
        """A file has been selected in the files table"""
        if not self.__is_file_selected():
            return
        # reenable all buttons but the first two which is handled based on status later
        self.btnFileRedownload.setEnabled(True)
        self.btnFileRemoveFromList.setEnabled(True)
        self.btnFileRemove.setEnabled(True)
        self.btnFileDetails.setEnabled(True)
        self.btnFileShowInFolder.setEnabled(True)
        self.btnFileCopyURL.setEnabled(True)
        self.btnFileOpenLink.setEnabled(True)

        file_status = self.tblFiles.item(
            self.tblFiles.currentRow(), MainWindow.FILE_STATUS_IDX
        ).text()
        self.__update_file_toolbar_buttons(file_status)

    def __is_file_selected(self, filename=None):
        """Determine whether a file is selected"""
        if filename is None:
            return (
                self.tblFiles.selectedItems() is not None
                and len(self.tblFiles.selectedItems()) > 0
            )
        else:
            return (
                self.tblFiles.selectedItems() is not None
                and len(self.tblFiles.selectedItems()) > 0
                and self.tblFiles.selectedItems()[0].text() == filename
            )

    def __on_file_start_download(self):
        """Start downloading the selected file"""
        # immediately set the button to disabled, reset if an error occurs later
        self.btnFileStartDownload.setEnabled(False)
        if not self.__is_job_selected() or not self.__is_file_selected():
            self.btnFileStartDownload.setEnabled(True)
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        ok, message = self.controller.start_download(job_name, file_name)
        if ok:
            # update files table view to Downloading in the status column
            self.tblFiles.setItem(
                self.tblFiles.currentRow(),
                MainWindow.FILE_STATUS_IDX,
                QTableWidgetItem(message),
            )
        else:
            self.__show_error_dialog("Failed to start download: " + message)
            self.btnFileStartDownload.setEnabled(True)

    def __on_file_stop_download(self):
        """Stop downloading the selected file"""
        # immediately set the button to disabled, reset if an error occurs later
        self.btnFileStopDownload.setEnabled(False)
        if not self.__is_job_selected() or not self.__is_file_selected():
            self.btnFileStopDownload.setEnabled(True)
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        ok, message = self.controller.stop_download(job_name, file_name)
        if ok:
            # update files table view to Downloading in the status column
            self.tblFiles.setItem(
                self.tblFiles.currentRow(),
                MainWindow.FILE_STATUS_IDX,
                QTableWidgetItem(message),
            )
        else:
            self.__show_error_dialog("Failed to stop download: " + message)
            self.btnFileStopDownload.setEnabled(True)

    def __on_file_redownload(self):
        """Redownload the selected file"""
        if confirmation_dialog(
            self,
            'Redownload file: "' + self.tblFiles.selectedItems()[0].text() + '"?',
        ):
            row = self.tblFiles.currentRow()
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRedownload.setEnabled(False)
            self.btnFileStartDownload.setEnabled(False)
            self.btnFileStopDownload.setEnabled(False)
            if not self.__is_job_selected() or not self.__is_file_selected():
                self.btnFileRedownload.setEnabled(True)
                self.__update_file_toolbar_buttons(
                    self.tblFiles.item(row, MainWindow.FILE_STATUS_IDX).text()
                )
                return
            job_name = self.tblJobs.selectedItems()[0].text()
            file_name = self.tblFiles.selectedItems()[0].text()
            self.__reset_rate_and_eta_for_file(file_name)
            ok, message = self.controller.redownload_file(job_name, file_name)
            if ok:
                # update files table view to Downloading in the status column
                self.tblFiles.setItem(
                    self.tblFiles.currentRow(),
                    MainWindow.FILE_STATUS_IDX,
                    QTableWidgetItem(message),
                )
            else:
                self.__show_error_dialog("Failed to redownload: " + message)
                self.btnFileRedownload.setEnabled(True)
                self.__reset_rate_and_eta_for_file(file_name)
            self.__update_file_toolbar_buttons(
                self.tblFiles.item(row, MainWindow.FILE_STATUS_IDX).text()
            )

    def __on_file_remove_from_list(self):
        """Remove the selected file from the list"""
        if confirmation_dialog(
            self,
            f"""You can re-add this file on the job editor screen.<br/>
            Remove file from list: <b>{self.tblFiles.selectedItems()[0].text()}</b>?""",
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemoveFromList.setEnabled(False)
            if not self.__is_job_selected() or not self.__is_file_selected():
                self.btnFileRemoveFromList.setEnabled(True)
                return
            job_name = self.tblJobs.selectedItems()[0].text()
            file_name = self.tblFiles.selectedItems()[0].text()
            ok, message = self.controller.remove_file_from_job(
                job_name, file_name, delete_from_disk=False
            )
            if ok:
                self.tblFiles.removeRow(self.tblFiles.currentRow())
            else:
                self.__show_error_dialog("Failed to remove from list: " + message)
            self.btnFileRemoveFromList.setEnabled(True)

    def __on_file_remove(self):
        """Remove the selected file from the list and delete the local file"""
        if confirmation_dialog(
            self,
            'Remove file from list and disk: <b>"'
            + self.tblFiles.selectedItems()[0].text()
            + '</b>"?',
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemoveFromList.setEnabled(False)
            if not self.__is_job_selected() or not self.__is_file_selected():
                self.btnFileRemoveFromList.setEnabled(True)
                return
            job_name = self.tblJobs.selectedItems()[0].text()
            file_name = self.tblFiles.selectedItems()[0].text()
            ok, message = self.controller.remove_file_from_job(
                job_name, file_name, delete_from_disk=True
            )
            if ok:
                self.tblFiles.removeRow(self.tblFiles.currentRow())
            else:
                self.__show_error_dialog("Failed to remove: " + message)
            self.btnFileRemoveFromList.setEnabled(True)

    def __on_file_details(self):
        """Show the details of the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            # show error that no files are selected
            self.__show_error_dialog("No file selected")
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        # if any of them is None, it means the job or file is not selected and we do nothing
        if job_name is None or file_name is None:
            return
        dlg = FileDetailsDialog(self.controller, job_name, file_name)
        val = dlg.exec()
        if val == 1:
            job = dlg.get_job()
            logger.info("New job created: %s", job.name)
            self.controller.add_job(job)
            self.__update_jobs_table()
        else:
            logger.debug("New job creation cancelled")

    def __on_file_show_in_folder(self):
        """Show the selected file in the file explorer"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        local_url = self.controller.resolve_local_file_path(job_name, file_name)
        parent_folder = os.path.dirname(local_url)
        QDesktopServices.openUrl(QUrl.fromLocalFile(parent_folder))

    def __on_file_copy_url(self):
        """Copy the URL of the selected file to the clipboard"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        url = self.controller.resolve_file_url(job_name, file_name)
        QApplication.clipboard().setText(url)

    def __on_file_open_link(self):
        """Open the URL of the selected file in the default browser"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        url = self.controller.resolve_file_url(job_name, file_name)
        QDesktopServices.openUrl(QUrl(url))

    def __show_error_dialog(
        self, message, title="Error", icon=QMessageBox.Icon.Critical
    ):
        error_dialog = QMessageBox()
        error_dialog.setText(message)
        error_dialog.setWindowTitle(title)
        error_dialog.exec()

    def __restyleFileProgressBar(self, row, style):
        """Disable the given cell in the files table"""
        progress_bar = self.tblFiles.cellWidget(row, MainWindow.FILE_PROGRESS_IDX)
        if progress_bar:
            progress_bar.setStyleSheet(style)

    def __reset_rate_and_eta_for_file(self, filename):
        """Reset the rate and ETA for the given file"""
        for row in range(self.tblFiles.rowCount()):
            if filename == self.tblFiles.item(row, MainWindow.FILE_NAME_IDX).text():
                self.__reset_rate_and_eta_for_row(row)
                break

    def __reset_rate_and_eta_for_row(self, row):
        """Reset the rate and ETA for the given row"""
        rate_item = self.tblFiles.item(row, MainWindow.FILE_RATE_IDX)
        if rate_item is not None:
            rate_item.setText("")
        eta_item = self.tblFiles.item(row, MainWindow.FILE_ETA_IDX)
        if eta_item is not None:
            eta_item.setText("")

    def __update_file_toolbar_buttons(self, status):
        """Update the file toolbar buttons based on the given status"""
        if status == FileModel.STATUS_DOWNLOADING:
            self.btnFileStartDownload.setEnabled(False)
            self.btnFileStopDownload.setEnabled(True)
        elif status == FileModel.STATUS_QUEUED:
            self.btnFileStartDownload.setEnabled(False)
            self.btnFileStopDownload.setEnabled(True)
        elif status == FileModel.STATUS_COMPLETED:
            self.btnFileStartDownload.setEnabled(False)
            self.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_FAILED:
            self.btnFileStartDownload.setEnabled(True)
            self.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_STOPPED:
            self.btnFileStartDownload.setEnabled(True)
            self.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_INVALID:
            self.btnFileStartDownload.setEnabled(True)
            self.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_NEW:
            self.btnFileStartDownload.setEnabled(True)
            self.btnFileStopDownload.setEnabled(False)

    def __job_size_str(self, job):
        """Return the size string for the given job"""
        if job.is_size_not_resolved():
            size = human_filesize(job.total_size_bytes)
            if size != "":
                return ">" + size
            else:
                return ""
        return human_filesize(job.total_size_bytes)

    def __set_job_progress_item(self, row, job):
        """Set the progress cell for the given job based on the current state of the job"""
        if job.is_size_not_resolved():
            self.tblJobs.removeCellWidget(row, MainWindow.JOB_PROGRESS_IDX)
            self.tblJobs.setItem(
                row,
                MainWindow.JOB_PROGRESS_IDX,
                QTableWidgetItem("Resolving size..."),
            )
            return
        if job.total_size_bytes is None or job.total_size_bytes == 0:
            self.tblJobs.setItem(
                row,
                MainWindow.JOB_PROGRESS_IDX,
                QTableWidgetItem("Unknown size"),
            )
            return

        progress_bar = self.tblJobs.cellWidget(row, MainWindow.JOB_PROGRESS_IDX)
        if progress_bar is None:
            progress_bar = QProgressBar()
            self.tblJobs.setCellWidget(row, MainWindow.JOB_PROGRESS_IDX, progress_bar)
        completion = int(100 * (job.downloaded_bytes or 0) / job.total_size_bytes)
        progress_bar.setValue(completion)
        progress_bar.setStyleSheet(
            MainWindow.PROGRESS_BAR_ACTIVE_STYLE
            if job.status == Job.STATUS_RUNNING
            else MainWindow.PROGRESS_BAR_PASSIVE_STYLE
        )

    def update_job(self, job: JobDTO):
        """Update the job in the table. Called by the cycle ticker."""
        for row in range(self.tblJobs.rowCount()):
            if job.name == self.tblJobs.item(row, MainWindow.JOB_NAME_IDX).text():
                self.__set_job_at_row(row, job)
                break

    def __set_job_at_row(self, row, job: JobDTO):
        """Set the job at the given row in the jobs table"""
        self.tblJobs.setItem(row, MainWindow.JOB_NAME_IDX, QTableWidgetItem(job.name))
        self.tblJobs.setItem(
            row, MainWindow.JOB_SIZE_IDX, QTableWidgetItem(self.__job_size_str(job))
        )
        self.tblJobs.setItem(
            row, MainWindow.JOB_STATUS_IDX, QTableWidgetItem(job.status)
        )
        self.tblJobs.setItem(
            row,
            MainWindow.JOB_RATE_IDX,
            QTableWidgetItem(
                human_rate(job.rate_bytes_per_sec)
                if job.status == Job.STATUS_RUNNING
                else ""
            ),
        )
        self.tblJobs.setItem(
            row,
            MainWindow.JOB_THREADS_IDX,
            QTableWidgetItem(f"{job.threads_active or 0}/{job.threads_allocated or 0}"),
        )
        self.tblJobs.setItem(
            row,
            MainWindow.JOB_FILES_IDX,
            QTableWidgetItem(f"{job.files_done or 0}/{job.selected_files_count or 0}"),
        )
        self.__set_job_progress_item(row, job)
        self.tblJobs.setItem(
            row,
            MainWindow.JOB_ETA_IDX,
            QTableWidgetItem(
                human_eta(
                    int(
                        (job.total_size_bytes - job.downloaded_bytes)
                        / job.rate_bytes_per_sec
                    )
                    if job.rate_bytes_per_sec and job.rate_bytes_per_sec > 0
                    else 0
                )
                if job.status == Job.STATUS_RUNNING
                else ""
            ),
        )
        self.tblJobs.setItem(
            row, MainWindow.JOB_TARGET_FOLDER_IDX, QTableWidgetItem(job.target_folder)
        )

    def __set_file_at_row(self, row, file: FileModelDTO):
        """Set the file at the given row in the files table. Reuses the existing widgets
        in the table if applicable, because creating new widgets is slow."""
        # NAME
        name_table_item = self.tblFiles.item(row, MainWindow.FILE_NAME_IDX)
        if name_table_item is None:
            self.tblFiles.setItem(
                row, MainWindow.FILE_NAME_IDX, QTableWidgetItem(file.name)
            )
        else:
            name_table_item.setText(file.name)
        # SIZE
        size_str = (
            human_filesize(file.size_bytes)
            if file.size_bytes is not None and file.size_bytes > -1
            else ""
        )
        size_table_item = self.tblFiles.item(row, MainWindow.FILE_SIZE_IDX)
        if size_table_item is None:
            self.tblFiles.setItem(
                row, MainWindow.FILE_SIZE_IDX, QTableWidgetItem(size_str)
            )
        else:
            size_table_item.setText(size_str)
        # STATUS
        status_table_item = self.tblFiles.item(row, MainWindow.FILE_STATUS_IDX)
        if status_table_item is None:
            status_table_item = QTableWidgetItem(file.status)
            self.tblFiles.setItem(row, MainWindow.FILE_STATUS_IDX, status_table_item)
        else:
            status_table_item.setText(file.status)
        # PROGRESS
        progress_bar = self.tblFiles.cellWidget(row, MainWindow.FILE_PROGRESS_IDX)
        if progress_bar is None:
            progress_bar = QProgressBar()
            self.tblFiles.setCellWidget(row, MainWindow.FILE_PROGRESS_IDX, progress_bar)
        progress_bar.setValue(
            file.percent_completed
            if file.percent_completed is not None and file.percent_completed > -1
            else 0
        )
        if file.status == FileModel.STATUS_DOWNLOADING:
            # ETA
            eta_str = human_eta(file.eta_seconds)
            eta_table_item = self.tblFiles.item(row, MainWindow.FILE_ETA_IDX)
            if eta_table_item is None:
                eta_table_item = QTableWidgetItem(eta_str)
                self.tblFiles.setItem(
                    row,
                    MainWindow.FILE_ETA_IDX,
                    eta_table_item,
                )
            else:
                eta_table_item.setText(eta_str)
            # RATE
            rate_str = human_rate(file.rate_bytes_per_sec)
            rate_table_item = self.tblFiles.item(row, MainWindow.FILE_RATE_IDX)
            if rate_table_item is None:
                rate_table_item = QTableWidgetItem(rate_str)
                self.tblFiles.setItem(
                    row,
                    MainWindow.FILE_RATE_IDX,
                    rate_table_item,
                )
            else:
                rate_table_item.setText(rate_str)
            self.__restyleFileProgressBar(row, MainWindow.PROGRESS_BAR_ACTIVE_STYLE)
        else:
            self.__reset_rate_and_eta_for_row(row)
            self.__restyleFileProgressBar(row, MainWindow.PROGRESS_BAR_PASSIVE_STYLE)

        # LAST UPDATED
        last_updated_timestamp_str = (
            human_timestamp_from(file.last_event_timestamp)
            if file.last_event_timestamp is not None
            else ""
        )
        last_updated_table_item = self.tblFiles.item(
            row, MainWindow.FILE_LAST_UPDATED_IDX
        )
        if last_updated_table_item is None:
            last_updated_table_item = QTableWidgetItem(last_updated_timestamp_str)
            self.tblFiles.setItem(
                row,
                MainWindow.FILE_LAST_UPDATED_IDX,
                QTableWidgetItem(last_updated_timestamp_str),
            )
        else:
            last_updated_table_item.setText(last_updated_timestamp_str)
        # LAST EVENT
        last_event_str = file.last_event or ""
        last_event_table_item = self.tblFiles.item(row, MainWindow.FILE_LAST_EVENT_IDX)
        if last_event_table_item is None:
            last_event_table_item = QTableWidgetItem(last_event_str)
            self.tblFiles.setItem(
                row, MainWindow.FILE_LAST_EVENT_IDX, last_event_table_item
            )
        else:
            last_event_table_item.setText(last_event_str)

    def update_file(self, file: FileModelDTO):
        """Update the file progress of the given file if the right job is selected"""
        if (
            self.__is_job_selected()
            and file.job_name == self.tblJobs.selectedItems()[0].text()
        ):
            for row in range(self.tblFiles.rowCount()):
                if (
                    file.name
                    == self.tblFiles.item(row, MainWindow.FILE_NAME_IDX).text()
                ):
                    self.__set_file_at_row(row, file)
                    break
            if self.__is_file_selected(file.name):
                self.__update_file_toolbar_buttons(file.status)
