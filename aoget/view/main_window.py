import os
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
from .main_window_data import MainWindowData
from model.file_model import FileModel

from aoget.view.new_job_dialog import NewJobDialog
from util.aogetutil import human_timestamp_from, human_filesize, human_eta, human_rate
from util.qt_util import confirmation_dialog

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
        if not self.__is_job_selected():
            return
        selected_job = self.tblJobs.selectedItems()[0].text()
        self.__show_files(self.window_data.get_job_by_name(selected_job))
        self.window_data.job_post_select(selected_job)

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
            progress_bar.setStyleSheet(
                MainWindow.PROGRESS_BAR_ACTIVE_STYLE
                if file.status == FileModel.STATUS_DOWNLOADING
                else MainWindow.PROGRESS_BAR_PASSIVE_STYLE
            )
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
        ok, message = self.window_data.stop_download(job_name, file_name)
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
            ok, message = self.window_data.redownload_file(job_name, file_name)
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
            Remove file from list: <b>{self.tblFiles.selectedItems()[0].text()}</b>?"""
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemoveFromList.setEnabled(False)
            if not self.__is_job_selected() or not self.__is_file_selected():
                self.btnFileRemoveFromList.setEnabled(True)
                return
            job_name = self.tblJobs.selectedItems()[0].text()
            file_name = self.tblFiles.selectedItems()[0].text()
            ok, message = self.window_data.deselect_file(job_name, file_name)
            if ok:
                self.tblFiles.removeRow(self.tblFiles.currentRow())
            else:
                self.__show_error_dialog("Failed to remove from list: " + message)
            self.btnFileRemoveFromList.setEnabled(True)

    def __on_file_remove(self):
        """Remove the selected file from the list and delete the local file"""
        if confirmation_dialog(
            'Remove file from list and disk: "'
            + self.tblFiles.selectedItems()[0].text()
            + '"?'
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemove.setEnabled(False)
            if not self.__is_job_selected() or not self.__is_file_selected():
                self.btnFileRemove.setEnabled(True)
                return
            job_name = self.tblJobs.selectedItems()[0].text()
            file_name = self.tblFiles.selectedItems()[0].text()
            ok, message = self.window_data.deselect_and_remove_file(job_name, file_name)
            if ok:
                self.tblFiles.removeRow(self.tblFiles.currentRow())
            else:
                self.__show_error_dialog("Failed to remove: " + message)
                self.btnFileRemove.setEnabled(True)

    def __on_file_details(self):
        """Show the details of the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        self.window_data.show_file_details(job_name, file_name)

    def __on_file_show_in_folder(self):
        """Show the selected file in the file explorer"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        local_url = self.window_data.resolve_local_file_path(job_name, file_name)
        parent_folder = os.path.dirname(local_url)
        QDesktopServices.openUrl(QUrl.fromLocalFile(parent_folder))

    def __on_file_copy_url(self):
        """Copy the URL of the selected file to the clipboard"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        url = self.window_data.resolve_file_url(job_name, file_name)
        QApplication.clipboard().setText(url)

    def __on_file_open_link(self):
        """Open the URL of the selected file in the default browser"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        file_name = self.tblFiles.selectedItems()[0].text()
        url = self.window_data.resolve_file_url(job_name, file_name)
        QDesktopServices.openUrl(QUrl(url))

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

    def __reset_rate_and_eta_for_file(self, filename):
        """Reset the rate and ETA for the given file"""
        for row in range(self.tblFiles.rowCount()):
            if filename == self.tblFiles.item(row, MainWindow.FILE_NAME_IDX).text():
                self.tblFiles.setItem(
                    row, MainWindow.FILE_RATE_IDX, QTableWidgetItem("")
                )
                self.tblFiles.setItem(
                    row, MainWindow.FILE_ETA_IDX, QTableWidgetItem("")
                )
                break

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
                        self.__reset_rate_and_eta_for_file(filename)
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
                        self.__reset_rate_and_eta_for_file(filename)
                        self.__restyleFileProgressBar(
                            row, MainWindow.PROGRESS_BAR_PASSIVE_STYLE
                        )
                    else:
                        self.__restyleFileProgressBar(
                            row, MainWindow.PROGRESS_BAR_ACTIVE_STYLE
                        )
                    break
            if self.__is_file_selected(filename):
                self.__update_file_toolbar_buttons(status)
