import logging
import os
import threading
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidgetItem,
    QProgressBar,
    QApplication,
)
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from util.aogetutil import human_filesize, human_eta, human_rate, human_timestamp_from
from util.qt_util import (
    error_dialog,
    confirmation_dialog,
    show_warnings,
)
from model.file_model import FileModel
from model.dto.file_model_dto import FileModelDTO
from view.file_status_widget_item import FileStatusWidgetItem
from view.priority_widget_item import PriorityWidgetItem
from view.rate_widget_item import RateWidgetItem
from view.size_widget_item import SizeWidgetItem
from view.file_details_dialog import FileDetailsDialog
from view import PROGRESS_BAR_ACTIVE_STYLE, PROGRESS_BAR_PASSIVE_STYLE

logger = logging.getLogger(__name__)


FILE_NAME_IDX = 0
FILE_SIZE_IDX = 1
FILE_PRIORITY_IDX = 2
FILE_STATUS_IDX = 3
FILE_PROGRESS_IDX = 4
FILE_RATE_IDX = 5
FILE_ETA_IDX = 6
FILE_LAST_UPDATED_IDX = 7
FILE_LAST_EVENT_IDX = 8


class MainWindowFiles:
    """Artificial extraction of the files-related UI controls and related methods from MainWindow.
    A better solution could be to use a Qt component, but that seems incompatible with Qt Designer.
    Signal defs remain in MainWindow but handler methods are in this class. A general pattern used
    in this class is to define mw as the main window object and use it as a handle to access the
    UI objects.
    """

    def __init__(self, main_window):
        """Initializes the MainWindowFiles object with a reference to the main window.
        :param main_window: The main window object."""
        self.main_window = main_window
        self.file_table_lock = threading.RLock()

    def setup_ui(self) -> None:
        """Sets up the UI for the files table."""
        self.__setup_table()

    def __setup_table(self) -> None:
        """Setup the files table and controls around it"""
        mw = self.main_window

        header_labels = [
            "Name",
            "Size",
            "Priority",
            "Status",
            "Progress",
            "Rate",
            "ETA",
            "Last Updated",
            "Last Event",
        ]

        mw.tblFiles.setColumnCount(len(header_labels))
        mw.tblFiles.setHorizontalHeaderLabels(header_labels)
        header = mw.tblFiles.horizontalHeader()
        header.setSectionResizeMode(FILE_NAME_IDX, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(FILE_SIZE_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(FILE_PRIORITY_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(FILE_STATUS_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(FILE_PROGRESS_IDX, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(FILE_RATE_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(FILE_ETA_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(
            FILE_LAST_UPDATED_IDX,
            QHeaderView.ResizeMode.Fixed,
        )
        header.setSectionResizeMode(FILE_LAST_EVENT_IDX, QHeaderView.ResizeMode.Stretch)
        mw.tblFiles.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        mw.tblFiles.setSelectionMode(QHeaderView.SelectionMode.ExtendedSelection)
        mw.tblFiles.verticalHeader().setHidden(True)
        column_widths = [200, 70, 100, 100, 300, 70, 100, 150, 300]
        for i, width in enumerate(column_widths):
            mw.tblFiles.setColumnWidth(i, width)

        # jobs table selection
        mw.tblFiles.itemSelectionChanged.connect(self.update_file_toolbar)

        # file toolbar buttons
        mw.btnFileStartDownload.clicked.connect(self.__on_file_start_download)
        mw.btnFileStopDownload.clicked.connect(self.__on_file_stop_download)
        mw.btnFileRedownload.clicked.connect(self.__on_file_redownload)
        mw.btnFileRemoveFromList.clicked.connect(self.__on_file_remove_from_list)
        mw.btnFileRemove.clicked.connect(self.__on_file_remove)
        mw.btnFileDetails.clicked.connect(self.__on_file_details)
        mw.btnFileShowInFolder.clicked.connect(self.__on_file_show_in_folder)
        mw.btnFileCopyURL.clicked.connect(self.__on_file_copy_url)
        mw.btnFileOpenLink.clicked.connect(self.__on_file_open_link)
        mw.btnFilePriorityPlus.clicked.connect(self.__on_file_priority_plus)
        mw.btnFilePriorityMinus.clicked.connect(self.__on_file_priority_minus)

        # disable all file toolbar buttons
        mw.btnFileStartDownload.setEnabled(False)
        mw.btnFileStopDownload.setEnabled(False)
        mw.btnFileRedownload.setEnabled(False)
        mw.btnFileRemoveFromList.setEnabled(False)
        mw.btnFileRemove.setEnabled(False)
        mw.btnFileDetails.setEnabled(False)
        mw.btnFileShowInFolder.setEnabled(False)
        mw.btnFileCopyURL.setEnabled(False)
        mw.btnFileOpenLink.setEnabled(False)
        mw.btnFilePriorityPlus.setEnabled(False)
        mw.btnFilePriorityMinus.setEnabled(False)

        # issue #110: redownload currently disabled
        mw.btnFileRedownload.setHidden(True)

    def show_files(self, job_name: str) -> None:
        """Shows the files for the selected job.
        :param job_name: The name of the selected job."""
        mw = self.main_window
        mw.tblFiles.setUpdatesEnabled(False)
        mw.tblFiles.blockSignals(True)
        if job_name is None:
            for i in range(0, mw.tblFiles.rowCount()):
                mw.tblFiles.setRowHidden(i, True)
        else:
            selected_files = mw.controller.files.get_selected_file_dtos(job_name).values()
            mw.tblFiles.setRowCount(mw.controller.files.get_largest_fileset_length())
            for i, file in enumerate(selected_files):
                self.set_file_at_row(i, file)
                mw.tblFiles.setRowHidden(i, False)
            # part of perf-optimization, we don't delete widgets, just hide the rows
            for i in range(len(selected_files), mw.tblFiles.rowCount()):
                mw.tblFiles.setRowHidden(i, True)
        mw.tblFiles.blockSignals(False)
        mw.tblFiles.setUpdatesEnabled(True)

    def get_current_file_status(self) -> str:
        """Get the status of the currently selected file"""
        mw = self.main_window
        current_row = mw.tblFiles.currentRow()
        item = mw.tblFiles.item(current_row, FILE_STATUS_IDX)
        return item.text() if item is not None else ""

    def update_file_toolbar(self) -> None:
        """A file has been selected in the files table"""
        mw = self.main_window
        job_name = mw.get_selected_job_name()

        if not self.is_file_selected() or job_name in mw.jobs_table_view.resuming_jobs:
            mw.btnFileStartDownload.setEnabled(False)
            mw.btnFileStopDownload.setEnabled(False)
            mw.btnFileRedownload.setEnabled(False)
            mw.btnFileRemoveFromList.setEnabled(False)
            mw.btnFileRemove.setEnabled(False)
            mw.btnFileDetails.setEnabled(False)
            mw.btnFileShowInFolder.setEnabled(False)
            mw.btnFileCopyURL.setEnabled(False)
            mw.btnFileOpenLink.setEnabled(False)
            mw.btnFilePriorityPlus.setEnabled(False)
            mw.btnFilePriorityMinus.setEnabled(False)

        elif self.__selected_file_count() == 1:
            mw.btnFileRedownload.setEnabled(True)
            mw.btnFileRemoveFromList.setEnabled(True)
            mw.btnFileRemove.setEnabled(True)
            mw.btnFileDetails.setEnabled(True)
            mw.btnFileShowInFolder.setEnabled(True)
            mw.btnFileCopyURL.setEnabled(True)
            mw.btnFileOpenLink.setEnabled(True)
            mw.btnFilePriorityPlus.setEnabled(True)
            mw.btnFilePriorityMinus.setEnabled(True)
            file_status = self.get_current_file_status()
            self.__update_file_start_stop_buttons(file_status)

        else:
            mw.btnFileStartDownload.setEnabled(True)
            mw.btnFileStopDownload.setEnabled(True)
            mw.btnFileRedownload.setEnabled(False)
            mw.btnFileRemoveFromList.setEnabled(True)
            mw.btnFileRemove.setEnabled(True)
            mw.btnFileDetails.setEnabled(False)
            mw.btnFileShowInFolder.setEnabled(False)
            mw.btnFileCopyURL.setEnabled(False)
            mw.btnFileOpenLink.setEnabled(False)
            mw.btnFilePriorityPlus.setEnabled(True)
            mw.btnFilePriorityMinus.setEnabled(True)

    def is_file_selected(self, filename=None) -> bool:
        """Determine whether a file is selected"""
        mw = self.main_window
        if filename is None:
            return (
                mw.tblFiles.selectedItems() is not None
                and len(mw.tblFiles.selectedItems()) > 0
            )
        else:
            return filename in self.selected_file_names()

    def get_current_selection(self) -> tuple[str, str]:
        """Get the selected job and file name"""
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        file_name = mw.tblFiles.selectedItems()[0].text()
        return job_name, file_name

    def get_current_multi_selection(self) -> tuple[str, list[str]]:
        """Get the selected job and file names"""
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        file_names = self.selected_file_names()
        return job_name, file_names

    def __selected_file_count(self) -> int:
        """Get the number of selected files"""
        mw = self.main_window
        selected_items = mw.tblFiles.selectedItems()
        if selected_items is None:
            return 0
        unique_rows = {item.row() for item in selected_items}
        return len(unique_rows)

    def selected_file_names(self) -> list[str]:
        """Get the names of the selected files"""
        mw = self.main_window
        selected_items = mw.tblFiles.selectedItems()
        unique_rows = set()
        first_column_values = []

        for item in selected_items:
            row = item.row()
            if row not in unique_rows:
                unique_rows.add(row)
                first_column_value = mw.tblFiles.item(row, 0).text()
                first_column_values.append(first_column_value)
        return first_column_values

    def nothing_selected(self) -> bool:
        """Returns True if nothing (no job, no file) is selected, False otherwise"""
        mw = self.main_window
        return not mw.is_job_selected() or not self.is_file_selected()

    def __hide_selected_row(self) -> None:
        """Hide the currently selected row in the files table"""
        mw = self.main_window
        with self.file_table_lock:
            idx = mw.tblFiles.selectionModel().selectedRows()[0].row()
            mw.tblFiles.setRowHidden(idx, True)

    def __hide_selected_rows(self) -> None:
        """Hide the currently selected rows in the files table"""
        mw = self.main_window
        with self.file_table_lock:
            selected_row_indexes = mw.tblFiles.selectionModel().selectedRows()
            for row_index in selected_row_indexes:
                mw.tblFiles.setRowHidden(row_index.row(), True)

    def __on_file_start_download(self) -> None:
        """Start downloading the selected file"""
        if not self.nothing_selected():
            if self.__selected_file_count() == 1:
                self.__single_file_download()
                return
            else:
                self.__multi_file_download()

    def __on_file_stop_download(self) -> None:
        """Stop downloading the selected file"""
        if not self.nothing_selected():
            if self.__selected_file_count() == 1:
                self.__single_file_stop_download()
                return
            else:
                self.__multi_file_stop_download()

    def __single_file_download(self) -> None:
        """Start downloading the currently selected file"""
        mw = self.main_window
        # immediately set the button to disabled, reset if an error occurs later
        mw.btnFileStartDownload.setEnabled(False)
        if self.nothing_selected():
            self.btnFileStartDownload.setEnabled(True)
            return
        job_name, file_name = self.get_current_selection()
        ok, message = mw.controller.files.start_download(job_name, file_name)
        if ok:
            # update files table view to Downloading in the status column
            mw.tblFiles.setItem(
                mw.tblFiles.currentRow(),
                FILE_STATUS_IDX,
                QTableWidgetItem(message),
            )
            mw.btnFileStopDownload.setEnabled(True)
        else:
            error_dialog(mw, "Failed to start download: " + message)
            logger.error("Failed to start download: %s", message)
            mw.btnFileStartDownload.setEnabled(True)

    def __multi_file_download(self) -> None:
        """Start downloading the currently selected files"""
        mw = self.main_window
        job_name, file_names = self.get_current_multi_selection()
        mw.controller.files.start_downloads(job_name, file_names)

    def __single_file_stop_download(self) -> None:
        """Stop downloading the currently selected file"""
        mw = self.main_window
        # immediately set the button to disabled, reset if an error occurs later
        mw.btnFileStopDownload.setEnabled(False)
        if self.nothing_selected():
            self.btnFileStopDownload.setEnabled(True)
            return
        job_name, file_name = self.get_current_selection()
        ok, message = mw.controller.files.stop_download(job_name, file_name)
        if ok:
            # update files table view to Downloading in the status column
            mw.tblFiles.setItem(
                mw.tblFiles.currentRow(),
                FILE_STATUS_IDX,
                QTableWidgetItem(message),
            )
            self.__update_file_start_stop_buttons(message)
        else:
            error_dialog(mw, "Failed to stop download: " + message)
            logger.error("Failed to stop download: %s", message)
            mw.btnFileStopDownload.setEnabled(True)

    def __multi_file_stop_download(self) -> None:
        """Stop downloading the selected files"""
        mw = self.main_window
        selected_job_name, selected_files = self.get_current_multi_selection()
        mw.controller.files.stop_downloads(selected_job_name, selected_files)

    def __on_file_redownload(self) -> None:
        """Redownload the selected file"""
        mw = self.main_window
        if confirmation_dialog(
            mw,
            'Redownload file: "' + mw.tblFiles.selectedItems()[0].text() + '"?',
        ):
            row = mw.tblFiles.currentRow()
            # immediately set the button to disabled, reset if an error occurs later
            mw.btnFileRedownload.setEnabled(False)
            mw.btnFileStartDownload.setEnabled(False)
            mw.btnFileStopDownload.setEnabled(False)
            if self.nothing_selected():
                mw.btnFileRedownload.setEnabled(True)
                self.__update_file_start_stop_buttons(
                    mw.tblFiles.item(row, FILE_STATUS_IDX).text()
                )
                return
            job_name, file_name = self.get_current_selection()
            self.__reset_rate_and_eta_for_file(file_name)
            ok, message = mw.controller.files.redownload_file(job_name, file_name)
            if ok:
                # update files table view to Downloading in the status column
                mw.tblFiles.setItem(
                    mw.tblFiles.currentRow(),
                    FILE_STATUS_IDX,
                    QTableWidgetItem(message),
                )
            else:
                error_dialog(self, "Failed to redownload: " + message)
                logger.error("Failed to redownload: %s", message)
                mw.btnFileRedownload.setEnabled(True)
                self.__reset_rate_and_eta_for_file(file_name)
            self.__update_file_start_stop_buttons(
                mw.tblFiles.item(row, FILE_STATUS_IDX).text()
            )

    def __on_file_remove_from_list(self) -> None:
        """Remove the currently selected file(s) from the list"""
        if self.nothing_selected():
            return
        if self.__selected_file_count() == 1:
            self.__single_file_remove_from_list()
            return
        else:
            self.__multi_file_remove_from_list()

    def __single_file_remove_from_list(self) -> None:
        """Remove the currently selected file from the list"""
        mw = self.main_window
        if confirmation_dialog(
            mw,
            f"""You can re-add this file on the job editor screen.<br/>
            Remove file from list: <b>{mw.tblFiles.selectedItems()[0].text()}</b>?""",
        ):
            # immediately set the button to disabled, reset if an error occurs later
            mw.btnFileRemoveFromList.setEnabled(False)
            job_name, file_name = self.get_current_selection()
            ok, message = mw.controller.files.remove_file_from_job(
                job_name, file_name, delete_from_disk=False
            )
            if ok:
                self.__hide_selected_row()
            else:
                error_dialog(mw, "Failed to remove from list: " + message)
                logger.error("Failed to remove from list: %s", message)
            mw.btnFileRemoveFromList.setEnabled(True)

    def __multi_file_remove_from_list(self) -> None:
        """Remove the selected files from the list"""
        mw = self.main_window
        if confirmation_dialog(
            mw,
            f"""Remove {self.__selected_file_count()} selected file(s) from list?<br/>
            You can re-add these files on the job editor screen.""",
        ):
            # immediately set the button to disabled, reset if an error occurs later
            mw.btnFileRemoveFromList.setEnabled(False)
            selected_job_name, selected_files = self.get_current_multi_selection()
            messages = mw.controller.files.remove_files_from_job(
                selected_job_name, selected_files
            )
            self.show_files(selected_job_name)
            self.__hide_selected_rows()
            mw.btnFileRemoveFromList.setEnabled(True)
            if messages:
                show_warnings(
                    mw, "Removed files with the following warnings:", messages
                )

    def __on_file_remove(self) -> None:
        """Remove the selected file from the list and delete the local file"""
        if self.nothing_selected():
            return
        if self.__selected_file_count() == 1:
            self.__single_file_remove()
            return
        else:
            self.__multi_file_remove()

    def __single_file_remove(self) -> None:
        """Remove the selected file from the list and delete the local file"""
        mw = self.main_window
        if confirmation_dialog(
            mw,
            'Remove file from list and disk: <b>"'
            + mw.tblFiles.selectedItems()[0].text()
            + '</b>"?',
        ):
            # immediately set the button to disabled, reset if an error occurs later
            mw.btnFileRemoveFromList.setEnabled(False)
            job_name, file_name = self.get_current_selection()
            ok, message = mw.controller.files.remove_file_from_job(
                job_name, file_name, delete_from_disk=True
            )
            if ok:
                self.__hide_selected_row()
            else:
                error_dialog(mw, "Failed to remove: " + message)
                logger.error("Failed to remove: %s", message)
            mw.btnFileRemoveFromList.setEnabled(True)

    def __multi_file_remove(self) -> None:
        """Remove the selected files from the list"""
        mw = self.main_window
        if confirmation_dialog(
            mw,
            f"""Remove {self.__selected_file_count()} selected file(s) from list
            <b> and disk</b>?<br/>You can re-add these files on the job editor
            screen.""",
        ):
            # immediately set the button to disabled, reset if an error occurs later
            mw.btnFileRemoveFromList.setEnabled(False)
            selected_job_name, selected_files = self.get_current_multi_selection()
            messages = mw.controller.files.remove_files_from_job(
                selected_job_name, selected_files, delete_from_disk=True
            )
            self.show_files(selected_job_name)
            self.__hide_selected_rows()
            mw.btnFileRemoveFromList.setEnabled(True)
            if messages:
                show_warnings(
                    mw, "Removed files with the following warnings:", messages
                )

    def __on_file_details(self) -> None:
        """Show the details of the selected file"""
        if self.nothing_selected():
            return
        mw = self.main_window
        job_name, file_name = self.get_current_selection()
        FileDetailsDialog(mw.controller, job_name, file_name).exec()

    def __on_file_show_in_folder(self) -> None:
        """Show the selected file in the file explorer"""
        if self.nothing_selected():
            return
        mw = self.main_window
        job_name, file_name = self.get_current_selection()
        local_url = mw.controller.files.resolve_local_file_path(job_name, file_name)
        parent_folder = os.path.dirname(local_url)
        QDesktopServices.openUrl(QUrl.fromLocalFile(parent_folder))

    def __on_file_copy_url(self) -> None:
        """Copy the URL of the selected file to the clipboard"""
        if self.nothing_selected():
            return
        mw = self.main_window
        job_name, file_name = self.get_current_selection()
        url = mw.controller.files.resolve_file_url(job_name, file_name)
        QApplication.clipboard().setText(url)

    def __on_file_open_link(self) -> None:
        """Open the URL of the selected file in the default browser"""
        if self.nothing_selected():
            return
        mw = self.main_window
        job_name, file_name = self.get_current_selection()
        url = mw.controller.files.resolve_file_url(job_name, file_name)
        QDesktopServices.openUrl(QUrl(url))

    def __on_file_priority_plus(self) -> None:
        """Increase the priority of the selected file"""
        if self.nothing_selected():
            return
        mw = self.main_window
        job_name, selected_files = self.get_current_multi_selection()
        mw.controller.files.increase_file_priorities(job_name, selected_files)

    def __on_file_priority_minus(self) -> None:
        """Decrease the priority of the selected file"""
        if self.nothing_selected():
            return
        mw = self.main_window
        job_name, selected_files = self.get_current_multi_selection()
        mw.controller.files.decrease_file_priorities(job_name, selected_files)

    def __restyleFileProgressBar(self, row: int, style: str) -> None:
        """Restyle the progress bar for the given row in the files table"""
        mw = self.main_window
        progress_bar = mw.tblFiles.cellWidget(row, FILE_PROGRESS_IDX)
        if progress_bar:
            progress_bar.setStyleSheet(style)

    def __reset_rate_and_eta_for_file(self, filename: str) -> None:
        """Reset the rate and ETA for the given file"""
        mw = self.main_window
        for row in range(mw.tblFiles.rowCount()):
            if filename == mw.tblFiles.item(row, FILE_NAME_IDX).text():
                self.__reset_rate_and_eta_for_row(row)
                break

    def __reset_rate_and_eta_for_row(self, row: int) -> None:
        """Reset the rate and ETA for the given row"""
        mw = self.main_window
        rate_item = mw.tblFiles.item(row, FILE_RATE_IDX)
        if rate_item is not None:
            rate_item.setText("")
        eta_item = mw.tblFiles.item(row, FILE_ETA_IDX)
        if eta_item is not None:
            eta_item.setText("")

    def __update_file_start_stop_buttons(self, status: str) -> None:
        """Update the file toolbar buttons based on the given status"""
        mw = self.main_window
        if status == FileModel.STATUS_DOWNLOADING:
            mw.btnFileStartDownload.setEnabled(False)
            mw.btnFileStopDownload.setEnabled(True)
        elif status == FileModel.STATUS_STOPPING:
            mw.btnFileStartDownload.setEnabled(False)
            mw.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_QUEUED:
            mw.btnFileStartDownload.setEnabled(False)
            mw.btnFileStopDownload.setEnabled(True)
        elif status == FileModel.STATUS_COMPLETED:
            mw.btnFileStartDownload.setEnabled(False)
            mw.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_FAILED:
            mw.btnFileStartDownload.setEnabled(True)
            mw.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_STOPPED:
            mw.btnFileStartDownload.setEnabled(True)
            mw.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_INVALID:
            mw.btnFileStartDownload.setEnabled(True)
            mw.btnFileStopDownload.setEnabled(False)
        elif status == FileModel.STATUS_NEW:
            mw.btnFileStartDownload.setEnabled(True)
            mw.btnFileStopDownload.setEnabled(False)

    def __priority_str(self, priority: int) -> str:
        """Return the priority string for the given priority"""
        if priority == FileModel.PRIORITY_HIGH:
            return "High"
        if priority == FileModel.PRIORITY_NORMAL:
            return "Normal"
        if priority == FileModel.PRIORITY_LOW:
            return "Low"
        return "Unknown"

    def set_file_at_row(self, row, file: FileModelDTO) -> None:
        """Set the file at the given row in the files table. Reuses the existing widgets
        in the table if applicable, because creating new widgets is slow."""
        mw = self.main_window
        # NAME
        name_table_item = mw.tblFiles.item(row, FILE_NAME_IDX)
        if name_table_item is None:
            name_table_item = QTableWidgetItem(file.name)
            mw.tblFiles.setItem(row, FILE_NAME_IDX, name_table_item)
        else:
            name_table_item.setText(file.name)
        name_table_item.setToolTip(file.name)
        # SIZE
        size_str = (
            human_filesize(file.size_bytes)
            if file.size_bytes is not None and file.size_bytes > -1
            else ""
        )
        size_table_item = mw.tblFiles.item(row, FILE_SIZE_IDX)
        if size_table_item is None:
            mw.tblFiles.setItem(row, FILE_SIZE_IDX, SizeWidgetItem(size_str))
        else:
            size_table_item.setText(size_str)
        # PRIORITY
        priority_str = self.__priority_str(file.priority)
        priority_table_item = mw.tblFiles.item(row, FILE_PRIORITY_IDX)
        if priority_table_item is None:
            priority_table_item = PriorityWidgetItem(priority_str)
            mw.tblFiles.setItem(row, FILE_PRIORITY_IDX, priority_table_item)
        else:
            priority_table_item.setText(priority_str)
        # STATUS
        status_table_item = mw.tblFiles.item(row, FILE_STATUS_IDX)
        if status_table_item is None:
            status_table_item = FileStatusWidgetItem(file.status)
            mw.tblFiles.setItem(row, FILE_STATUS_IDX, status_table_item)
        else:
            status_table_item.setText(file.status)
        # PROGRESS
        progress_bar = mw.tblFiles.cellWidget(row, FILE_PROGRESS_IDX)
        if progress_bar is None:
            progress_bar = QProgressBar()
            mw.tblFiles.setCellWidget(row, FILE_PROGRESS_IDX, progress_bar)
        progress_bar.setValue(
            file.percent_completed
            if file.percent_completed is not None and file.percent_completed > -1
            else 0
        )
        if file.status == FileModel.STATUS_DOWNLOADING:
            # ETA
            eta_str = human_eta(file.eta_seconds)
            eta_table_item = mw.tblFiles.item(row, FILE_ETA_IDX)
            if eta_table_item is None:
                eta_table_item = QTableWidgetItem(eta_str)
                mw.tblFiles.setItem(
                    row,
                    FILE_ETA_IDX,
                    eta_table_item,
                )
            else:
                eta_table_item.setText(eta_str)
            # RATE
            rate_str = human_rate(file.rate_bytes_per_sec)
            rate_table_item = mw.tblFiles.item(row, FILE_RATE_IDX)
            if rate_table_item is None:
                rate_table_item = RateWidgetItem(rate_str)
                mw.tblFiles.setItem(
                    row,
                    FILE_RATE_IDX,
                    rate_table_item,
                )
            else:
                rate_table_item.setText(rate_str)
            self.__restyleFileProgressBar(row, PROGRESS_BAR_ACTIVE_STYLE)
        else:
            self.__reset_rate_and_eta_for_row(row)
            self.__restyleFileProgressBar(row, PROGRESS_BAR_PASSIVE_STYLE)

        # LAST UPDATED
        last_updated_timestamp_str = (
            human_timestamp_from(file.last_event_timestamp)
            if file.last_event_timestamp is not None
            else ""
        )
        last_updated_table_item = mw.tblFiles.item(row, FILE_LAST_UPDATED_IDX)
        if last_updated_table_item is None:
            last_updated_table_item = QTableWidgetItem(last_updated_timestamp_str)
            mw.tblFiles.setItem(
                row,
                FILE_LAST_UPDATED_IDX,
                QTableWidgetItem(last_updated_timestamp_str),
            )
        else:
            last_updated_table_item.setText(last_updated_timestamp_str)
        # LAST EVENT
        last_event_str = file.last_event or ""
        last_event_table_item = mw.tblFiles.item(row, FILE_LAST_EVENT_IDX)
        if last_event_table_item is None:
            last_event_table_item = QTableWidgetItem(last_event_str)
            mw.tblFiles.setItem(row, FILE_LAST_EVENT_IDX, last_event_table_item)
        else:
            last_event_table_item.setText(last_event_str)
        last_event_table_item.setToolTip(last_event_str)

    def update_file(self, file: FileModelDTO):
        """Update the file progress of the given file if the right job is selected"""
        mw = self.main_window
        if file.job_name == mw.get_selected_job_name():
            for row in range(mw.tblFiles.rowCount()):
                if file.name == mw.tblFiles.item(row, FILE_NAME_IDX).text():
                    self.set_file_at_row(row, file)
                    break
            if self.is_file_selected(file.name):
                self.__update_file_start_stop_buttons(file.status)
