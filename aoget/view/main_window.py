import os
import threading
import logging
from PyQt6.QtWidgets import (
    QMainWindow,
    QHeaderView,
    QTableWidgetItem,
    QProgressBar,
    QMessageBox,
    QApplication,
    QFileDialog,
)
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from controller.main_window_controller import MainWindowController

from view.job_editor_dialog import JobEditorDialog
from view.file_details_dialog import FileDetailsDialog
from view.crash_report_dialog import CrashReportDialog
from view.app_settings_dialog import AppSettingsDialog
from view.translucent_widget import TranslucentWidget
from util.aogetutil import human_timestamp_from, human_filesize, human_eta, human_rate
from util.qt_util import confirmation_dialog, show_warnings, message_dialog
from config.app_config import AppConfig, get_config_value
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
    FILE_PRIORITY_IDX = 2
    FILE_STATUS_IDX = 3
    FILE_PROGRESS_IDX = 4
    FILE_RATE_IDX = 5
    FILE_ETA_IDX = 6
    FILE_LAST_UPDATED_IDX = 7
    FILE_LAST_EVENT_IDX = 8

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
    message_signal = pyqtSignal(str, str)
    job_resumed_signal = pyqtSignal(str, str, str)

    def __init__(self, aoget_db: AogetDb):
        super(MainWindow, self).__init__()
        self.controller = MainWindowController(self, aoget_db)
        uic.loadUi("aoget/qt/main_window.ui", self)
        self.file_table_lock = threading.RLock()
        self.closing = False
        self.resuming_jobs = []
        self.__setup_ui()
        self.show()
        self.controller.resume_state()

    def __setup_ui(self):
        """Setup the UI"""

        # connect signals
        self.update_job_signal.connect(self.update_job)
        self.update_file_signal.connect(self.update_file)
        self.message_signal.connect(self.show_message)
        self.job_resumed_signal.connect(self.job_resumed)
        self.actionOpen_GitHub_page.triggered.connect(self.open_github_page)
        self.actionSettings.triggered.connect(self.open_settings)
        self.actionExit.triggered.connect(self.close_app)
        self.actionPause_all.triggered.connect(self.pause_all)
        self.actionResume_all.triggered.connect(self.resume_all)

        self.__setup_bandwidth_limit_menu()
        self.__setup_jobs_table()
        self.__setup_files_table()
        self.__populate()
        self.__setup_overlays()
        self.__on_bandwidth_unlimited()
        self.__update_job_toolbar()

    def __setup_bandwidth_limit_menu(self):
        """Setup the bandwidth limit menu"""
        self.menuSet_global_bandwidth_limit.clear()
        self.menuSet_global_bandwidth_limit.addAction("Unlimited").triggered.connect(
            self.__on_bandwidth_unlimited
        )
        high_bandwidth_value = get_config_value(AppConfig.HIGH_BANDWIDTH_LIMIT) * 1024
        self.menuSet_global_bandwidth_limit.addAction(
            human_rate(high_bandwidth_value)
        ).triggered.connect(self.__on_bandwidth_high)
        medium_bandwidth_value = (
            get_config_value(AppConfig.MEDIUM_BANDWIDTH_LIMIT) * 1024
        )
        self.menuSet_global_bandwidth_limit.addAction(
            human_rate(medium_bandwidth_value)
        ).triggered.connect(self.__on_bandwidth_medium)
        low_bandwidth_value = get_config_value(AppConfig.LOW_BANDWIDTH_LIMIT) * 1024
        self.menuSet_global_bandwidth_limit.addAction(
            human_rate(low_bandwidth_value)
        ).triggered.connect(self.__on_bandwidth_low)
        # set them checkable
        for action in self.menuSet_global_bandwidth_limit.actions():
            action.setCheckable(True)
            action.setToolTip(
                "Youn can adjust these limits in the application settings."
            )

    def __setup_overlays(self):
        self.shutdown_overlay = TranslucentWidget(
            self,
            ("Shutting down..."),
        )
        self.shutdown_overlay.resize(self.width(), self.height())
        self.shutdown_overlay.hide()

    def __on_bandwidth_unlimited(self):
        self.controller.set_global_bandwidth_limit(0)
        # tick the menu item
        self.menuSet_global_bandwidth_limit.actions()[0].setChecked(True)
        # untick all other menu items
        for action in self.menuSet_global_bandwidth_limit.actions()[1:]:
            action.setChecked(False)

    def __on_bandwidth_high(self):
        limit = get_config_value(AppConfig.HIGH_BANDWIDTH_LIMIT) * 1024
        self.controller.set_global_bandwidth_limit(limit)
        # tick the menu item
        self.menuSet_global_bandwidth_limit.actions()[1].setChecked(True)
        # untick all other menu items
        for action in (
            self.menuSet_global_bandwidth_limit.actions()[0:1]
            + self.menuSet_global_bandwidth_limit.actions()[2:]
        ):
            action.setChecked(False)

    def __on_bandwidth_medium(self):
        limit = get_config_value(AppConfig.MEDIUM_BANDWIDTH_LIMIT) * 1024
        self.controller.set_global_bandwidth_limit(limit)
        # tick the menu item
        self.menuSet_global_bandwidth_limit.actions()[2].setChecked(True)
        # untick all other menu items
        for action in (
            self.menuSet_global_bandwidth_limit.actions()[0:2]
            + self.menuSet_global_bandwidth_limit.actions()[3:]
        ):
            action.setChecked(False)

    def __on_bandwidth_low(self):
        limit = get_config_value(AppConfig.LOW_BANDWIDTH_LIMIT) * 1024
        self.controller.set_global_bandwidth_limit(limit)
        # tick the menu item
        self.menuSet_global_bandwidth_limit.actions()[3].setChecked(True)
        # untick all other menu items
        for action in self.menuSet_global_bandwidth_limit.actions()[0:3]:
            action.setChecked(False)

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

        self.btnFileRedownload.setHidden(True)

        # job control buttons
        self.btnJobStart.clicked.connect(self.__on_job_start)
        self.btnJobStop.clicked.connect(self.__on_job_stop)
        self.btnJobThreadsPlus.clicked.connect(self.__on_job_threads_plus)
        self.btnJobThreadsMinus.clicked.connect(self.__on_job_threads_minus)
        self.btnJobCreate.clicked.connect(self.__on_create_new_job)
        self.btnJobEdit.clicked.connect(self.__on_edit_job)
        self.btnJobRemoveFromList.clicked.connect(self.__on_job_remove_from_list)
        self.btnJobRemove.clicked.connect(self.__on_job_remove_from_disk)
        self.btnJobExport.clicked.connect(self.__on_job_export)
        self.btnJobImport.clicked.connect(self.__on_job_import)
        self.btnJobOpenLink.clicked.connect(self.__on_job_open_link)
        self.btnJobHealthCheck.clicked.connect(self.__on_job_health_check)

        # jobs table selection
        self.tblJobs.itemSelectionChanged.connect(self.__on_job_selected)

    def __setup_files_table(self):
        """Setup the files table and controls around it"""
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

        self.tblFiles.setColumnCount(len(header_labels))
        self.tblFiles.setHorizontalHeaderLabels(header_labels)
        header = self.tblFiles.horizontalHeader()
        header.setSectionResizeMode(
            MainWindow.FILE_NAME_IDX, QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            MainWindow.FILE_SIZE_IDX, QHeaderView.ResizeMode.Fixed
        )
        header.setSectionResizeMode(
            MainWindow.FILE_PRIORITY_IDX, QHeaderView.ResizeMode.Fixed
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
        self.tblFiles.setSelectionMode(QHeaderView.SelectionMode.ExtendedSelection)
        column_widths = [200, 70, 100, 100, 300, 70, 100, 150, 300]
        for i, width in enumerate(column_widths):
            self.tblFiles.setColumnWidth(i, width)

        # Make columns sortable
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.__sort_files_table)

        # jobs table selection
        self.tblFiles.itemSelectionChanged.connect(self.__update_file_toolbar)

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
        self.btnFilePriorityPlus.clicked.connect(self.__on_file_priority_plus)
        self.btnFilePriorityMinus.clicked.connect(self.__on_file_priority_minus)

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
        self.btnFilePriorityPlus.setEnabled(False)
        self.btnFilePriorityMinus.setEnabled(False)

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
        self.__update_job_toolbar()
        self.__show_files(selected_job_name)
        self.controller.job_post_select(selected_job_name)

    def __on_job_start(self):
        """Start the selected job"""
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        self.controller.start_job(job_name)

    def __on_job_stop(self):
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        self.controller.stop_job(job_name)

    def __on_job_threads_plus(self):
        if not self.__is_job_selected():
            return
        current_job = self.tblJobs.selectedItems()[0].text()
        self.controller.add_thread(current_job)

    def __on_job_threads_minus(self):
        if not self.__is_job_selected():
            return
        current_job = self.tblJobs.selectedItems()[0].text()
        self.controller.remove_thread(current_job)

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
                self.controller.job_post_select(newly_selected_job, is_new=True)
            elif get_config_value(AppConfig.AUTO_START_JOBS):
                self.controller.start_job(dlg.controller.job.name)

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
            try:
                messages = self.controller.delete_job(job_name)
                if messages:
                    show_warnings(
                        self, "Removed job with the following warnings:", messages
                    )
                self.__update_jobs_table()
                # deselect table
                self.tblJobs.clearSelection()
                self.__show_files(None)
            except Exception as e:
                self.__show_error_dialog("Failed to remove job: " + str(e))
                logger.error("Failed to remove job: %s", job_name, exc_info=True)
                logger.exception(e)

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
            try:
                messages = self.controller.delete_job(job_name, delete_from_disk=True)
                if messages:
                    show_warnings(
                        self, "Removed job with the following warnings:", messages
                    )
                self.__update_jobs_table()
                # deselect table
                self.tblJobs.clearSelection()
                self.__show_files(None)
            except Exception as e:
                self.__show_error_dialog("Failed to remove job: " + str(e))
                logger.error("Failed to remove job: %s", job_name, exc_info=True)
                logger.exception(e)

    def __on_job_export(self):
        """Export the selected job"""
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        job_dto = self.controller.get_job_dto_by_name(job_name)
        if job_dto.is_size_not_resolved():
            self.__show_error_dialog(
                "Job size is not fully resolved. Please wait for the job to resolve its size before exporting."
            )
            return

        file, _ = QFileDialog.getSaveFileName(
            self, "Export Job", "", "YAML files (*.yaml)"
        )
        self.controller.export_job(job_name, file)

    def __on_job_import(self):
        """Import a job"""
        selected_job_name = (
            self.tblJobs.selectedItems()[0].text() if self.__is_job_selected() else None
        )
        file, _ = QFileDialog.getOpenFileName(
            self, "Import Job", "", "YAML files (*.yaml)"
        )
        if file:
            try:
                job_dto, file_dtos = self.controller.import_job(file)
                dlg = JobEditorDialog(
                    self.controller, job_dto=job_dto, file_dtos=file_dtos
                )
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
                        self.controller.job_post_select(newly_selected_job, is_new=True)
                    elif get_config_value(AppConfig.AUTO_START_JOBS):
                        self.controller.start_job(dlg.controller.job.name)
            except Exception as e:
                self.__show_error_dialog("Failed to import job: " + str(e))

    def __on_job_open_link(self):
        """Open the link of the selected job"""
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        job_dto = self.controller.get_job_dto_by_name(job_name)
        if job_dto and job_dto.page_url:
            QDesktopServices.openUrl(QUrl(job_dto.page_url))
        else:
            self.__show_error_dialog(
                "The job doesn't seem to have an associated link.<br/>Perhaps it was imported?"
            )

    def __on_job_health_check(self):
        """Perform a health check on the selected job"""
        if not self.__is_job_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        if confirmation_dialog(
            self,
            f"""Perform an integrity check on the job: <b>{job_name}</b>?<br>
            <p>This will check the status of all files in the job and update their status if necessary.<br/>
            Checks will be limited to files for which size is known, are currently not downloading and 
            already should be on disk (partially or completely downloaded).</p>
            <p>The process will not check the remote links for availability. 
            It will be done in the background, with failing files being updated as the process goes.</p>""",
        ):
            self.controller.health_check(job_name, self.message_signal)

    def __show_files(self, job_name):
        """Show the files of the given job in the files table."""
        if job_name is None:
            for i in range(0, self.tblFiles.rowCount()):
                self.tblFiles.setRowHidden(i, True)
            return
        selected_files = self.controller.get_selected_file_dtos(job_name).values()
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

    def __update_job_toolbar(self):
        """Update the job toolbar buttons based on the selected job"""
        job_name = (
            self.tblJobs.selectedItems()[0].text() if self.__is_job_selected() else None
        )
        if job_name is None or job_name in self.resuming_jobs:
            self.btnJobStart.setEnabled(False)
            self.btnJobStop.setEnabled(False)
            self.btnJobThreadsPlus.setEnabled(False)
            self.btnJobThreadsMinus.setEnabled(False)
            self.btnJobCreate.setEnabled(True)
            self.btnJobEdit.setEnabled(False)
            self.btnJobRemoveFromList.setEnabled(False)
            self.btnJobRemove.setEnabled(False)
            self.btnJobExport.setEnabled(False)
            self.btnJobImport.setEnabled(True)
            self.btnJobOpenLink.setEnabled(False)
            self.btnJobHealthCheck.setEnabled(False)
            if job_name in self.resuming_jobs:
                self.btnJobStart.setToolTip(
                    "Job is being resumed, please wait."
                )
                self.btnJobStop.setToolTip(
                    "Job is being resumed, please wait."
                )
        else:
            self.btnJobCreate.setEnabled(True)
            self.btnJobEdit.setEnabled(True)
            self.btnJobExport.setEnabled(True)
            self.btnJobImport.setEnabled(True)
            self.btnJobStart.setEnabled(True)
            self.btnJobStop.setEnabled(True)
            self.btnJobThreadsPlus.setEnabled(True)
            self.btnJobThreadsMinus.setEnabled(True)
            self.btnJobRemoveFromList.setEnabled(True)
            self.btnJobRemove.setEnabled(True)
            self.btnJobOpenLink.setEnabled(True)
            self.btnJobHealthCheck.setEnabled(True)
            self.btnJobStart.setToolTip("Start / resume downloading all files")
            self.btnJobStop.setToolTip("Stop downloading all files")

    def __update_file_toolbar(self):
        """A file has been selected in the files table"""
        job_name = (
            self.tblJobs.selectedItems()[0].text() if self.__is_job_selected() else None
        )

        if not self.__is_file_selected() or job_name in self.resuming_jobs:
            self.btnFileStartDownload.setEnabled(False)
            self.btnFileStopDownload.setEnabled(False)
            self.btnFileRedownload.setEnabled(False)
            self.btnFileRemoveFromList.setEnabled(False)
            self.btnFileRemove.setEnabled(False)
            self.btnFileDetails.setEnabled(False)
            self.btnFileShowInFolder.setEnabled(False)
            self.btnFileCopyURL.setEnabled(False)
            self.btnFileOpenLink.setEnabled(False)
            self.btnFilePriorityPlus.setEnabled(False)
            self.btnFilePriorityMinus.setEnabled(False)

        elif self.__selected_file_count() == 1:
            self.btnFileRedownload.setEnabled(True)
            self.btnFileRemoveFromList.setEnabled(True)
            self.btnFileRemove.setEnabled(True)
            self.btnFileDetails.setEnabled(True)
            self.btnFileShowInFolder.setEnabled(True)
            self.btnFileCopyURL.setEnabled(True)
            self.btnFileOpenLink.setEnabled(True)
            self.btnFilePriorityPlus.setEnabled(True)
            self.btnFilePriorityMinus.setEnabled(True)
            file_status = self.tblFiles.item(
                self.tblFiles.currentRow(), MainWindow.FILE_STATUS_IDX
            ).text()
            self.__update_file_start_stop_buttons(file_status)

        else:
            self.btnFileStartDownload.setEnabled(True)
            self.btnFileStopDownload.setEnabled(True)
            self.btnFileRedownload.setEnabled(False)
            self.btnFileRemoveFromList.setEnabled(True)
            self.btnFileRemove.setEnabled(True)
            self.btnFileDetails.setEnabled(False)
            self.btnFileShowInFolder.setEnabled(False)
            self.btnFileCopyURL.setEnabled(False)
            self.btnFileOpenLink.setEnabled(False)
            self.btnFilePriorityPlus.setEnabled(True)
            self.btnFilePriorityMinus.setEnabled(True)

    def __is_file_selected(self, filename=None):
        """Determine whether a file is selected"""
        if filename is None:
            return (
                self.tblFiles.selectedItems() is not None
                and len(self.tblFiles.selectedItems()) > 0
            )
        else:
            return filename in self.__selected_file_names()

    def __selected_file_count(self):
        """Get the number of selected files"""
        selected_items = self.tblFiles.selectedItems()
        if selected_items is None:
            return 0
        unique_rows = {item.row() for item in selected_items}
        return len(unique_rows)

    def __selected_file_names(self):
        selected_items = self.tblFiles.selectedItems()
        unique_rows = set()
        first_column_values = []

        for item in selected_items:
            row = item.row()
            if row not in unique_rows:
                unique_rows.add(row)
                first_column_value = self.tblFiles.item(row, 0).text()
                first_column_values.append(first_column_value)
        return first_column_values

    def __on_file_start_download(self):
        """Start downloading the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        if self.__selected_file_count() == 1:
            self.__single_file_download()
            return
        else:
            self.__multi_file_download()

    def __on_file_stop_download(self):
        """Stop downloading the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        if self.__selected_file_count() == 1:
            self.__single_file_stop_download()
            return
        else:
            self.__multi_file_stop_download()

    def __single_file_download(self):
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
            self.btnFileStopDownload.setEnabled(True)
        else:
            self.__show_error_dialog("Failed to start download: " + message)
            self.btnFileStartDownload.setEnabled(True)

    def __multi_file_download(self):
        """Start downloading the selected files"""
        selected_job_name = self.tblJobs.selectedItems()[0].text()
        selected_files = self.__selected_file_names()
        self.controller.start_downloads(selected_job_name, selected_files)

    def __single_file_stop_download(self):
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
            self.__update_file_start_stop_buttons(message)
        else:
            self.__show_error_dialog("Failed to stop download: " + message)
            self.btnFileStopDownload.setEnabled(True)

    def __multi_file_stop_download(self):
        """Stop downloading the selected files"""
        selected_job_name = self.tblJobs.selectedItems()[0].text()
        selected_files = self.__selected_file_names()
        self.controller.stop_downloads(selected_job_name, selected_files)

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
                self.__update_file_start_stop_buttons(
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
            self.__update_file_start_stop_buttons(
                self.tblFiles.item(row, MainWindow.FILE_STATUS_IDX).text()
            )

    def __on_file_remove_from_list(self):
        """Remove the selected file from the list"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        if self.__selected_file_count() == 1:
            self.__single_file_remove_from_list()
            return
        else:
            self.__multi_file_remove_from_list()

    def __single_file_remove_from_list(self):
        if confirmation_dialog(
            self,
            f"""You can re-add this file on the job editor screen.<br/>
            Remove file from list: <b>{self.tblFiles.selectedItems()[0].text()}</b>?""",
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemoveFromList.setEnabled(False)
            job_name = self.tblJobs.selectedItems()[0].text()
            file_name = self.tblFiles.selectedItems()[0].text()
            ok, message = self.controller.remove_file_from_job(
                job_name, file_name, delete_from_disk=False
            )
            if ok:
                with self.file_table_lock:
                    idx = self.tblFiles.selectionModel().selectedRows()[0].row()
                    self.tblFiles.setRowHidden(idx, True)
            else:
                self.__show_error_dialog("Failed to remove from list: " + message)
            self.btnFileRemoveFromList.setEnabled(True)

    def __multi_file_remove_from_list(self):
        """Remove the selected files from the list"""
        if confirmation_dialog(
            self,
            f"""Remove {self.__selected_file_count()} selected file(s) from list?<br/>
            You can re-add these files on the job editor screen.""",
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemoveFromList.setEnabled(False)
            selected_job_name = self.tblJobs.selectedItems()[0].text()
            selected_files = self.__selected_file_names()
            messages = self.controller.remove_files_from_job(
                selected_job_name, selected_files
            )
            self.__show_files(selected_job_name)
            with self.file_table_lock:
                selected_row_indexes = self.tblFiles.selectionModel().selectedRows()
                for row_index in selected_row_indexes:
                    self.tblFiles.setRowHidden(row_index.row(), True)
            self.btnFileRemoveFromList.setEnabled(True)
            if messages:
                show_warnings(
                    self, "Removed files with the following warnings:", messages
                )

    def __on_file_remove(self):
        """Remove the selected file from the list and delete the local file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        if self.__selected_file_count() == 1:
            self.__single_file_remove()
            return
        else:
            self.__multi_file_remove()

    def __single_file_remove(self):
        if confirmation_dialog(
            self,
            'Remove file from list and disk: <b>"'
            + self.tblFiles.selectedItems()[0].text()
            + '</b>"?',
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemoveFromList.setEnabled(False)
            job_name = self.tblJobs.selectedItems()[0].text()
            file_name = self.tblFiles.selectedItems()[0].text()
            ok, message = self.controller.remove_file_from_job(
                job_name, file_name, delete_from_disk=True
            )
            if ok:
                with self.file_table_lock:
                    idx = self.tblFiles.selectionModel().selectedRows()[0].row()
                    self.tblFiles.setRowHidden(idx, True)
                self.__show_error_dialog("Failed to remove: " + message)
            self.btnFileRemoveFromList.setEnabled(True)

    def __multi_file_remove(self):
        """Remove the selected files from the list"""
        if confirmation_dialog(
            self,
            f"""Remove {self.__selected_file_count()} selected file(s) from list <b> and disk</b>?<br/>
            You can re-add these files on the job editor screen.""",
        ):
            # immediately set the button to disabled, reset if an error occurs later
            self.btnFileRemoveFromList.setEnabled(False)
            selected_job_name = self.tblJobs.selectedItems()[0].text()
            selected_files = self.__selected_file_names()
            messages = self.controller.remove_files_from_job(
                selected_job_name, selected_files, delete_from_disk=True
            )
            self.__show_files(selected_job_name)
            with self.file_table_lock:
                selected_row_indexes = self.tblFiles.selectionModel().selectedRows()
                for row_index in selected_row_indexes:
                    self.tblFiles.setRowHidden(row_index.row(), True)
            self.btnFileRemoveFromList.setEnabled(True)
            if messages:
                show_warnings(
                    self, "Removed files with the following warnings:", messages
                )

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

    def __on_file_priority_plus(self):
        """Increase the priority of the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        selected_files = self.__selected_file_names()
        self.controller.increase_file_priorities(job_name, selected_files)

    def __on_file_priority_minus(self):
        """Decrease the priority of the selected file"""
        if not self.__is_job_selected() or not self.__is_file_selected():
            return
        job_name = self.tblJobs.selectedItems()[0].text()
        selected_files = self.__selected_file_names()
        self.controller.decrease_file_priorities(job_name, selected_files)

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

    def __update_file_start_stop_buttons(self, status):
        """Update the file toolbar buttons based on the given status"""
        if status == FileModel.STATUS_DOWNLOADING:
            self.btnFileStartDownload.setEnabled(False)
            self.btnFileStopDownload.setEnabled(True)
        elif status == FileModel.STATUS_STOPPING:
            self.btnFileStartDownload.setEnabled(False)
            self.btnFileStopDownload.setEnabled(False)
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

    def update_job(self, job: JobDTO) -> None:
        """Update the job in the table. Called by the cycle ticker."""
        for row in range(self.tblJobs.rowCount()):
            if job.name == self.tblJobs.item(row, MainWindow.JOB_NAME_IDX).text():
                self.__set_job_at_row(row, job)
                break

    def __get_row_index_of_job(self, job_name: str) -> int:
        """Return the row of the job with the given name"""
        for row in range(self.tblJobs.rowCount()):
            if job_name == self.tblJobs.item(row, MainWindow.JOB_NAME_IDX).text():
                return row
        return None

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

    def __priority_str(self, priority):
        """Return the priority string for the given priority"""
        if priority == FileModel.PRIORITY_HIGH:
            return "High"
        if priority == FileModel.PRIORITY_NORMAL:
            return "Normal"
        if priority == FileModel.PRIORITY_LOW:
            return "Low"
        return "Unknown"

    def __set_file_at_row(self, row, file: FileModelDTO):
        """Set the file at the given row in the files table. Reuses the existing widgets
        in the table if applicable, because creating new widgets is slow."""
        with self.file_table_lock:
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
            # PRIORITY
            priority_str = self.__priority_str(file.priority)
            priority_table_item = self.tblFiles.item(row, MainWindow.FILE_PRIORITY_IDX)
            if priority_table_item is None:
                priority_table_item = QTableWidgetItem(priority_str)
                self.tblFiles.setItem(
                    row, MainWindow.FILE_PRIORITY_IDX, priority_table_item
                )
            else:
                priority_table_item.setText(priority_str)
            # STATUS
            status_table_item = self.tblFiles.item(row, MainWindow.FILE_STATUS_IDX)
            if status_table_item is None:
                status_table_item = QTableWidgetItem(file.status)
                self.tblFiles.setItem(
                    row, MainWindow.FILE_STATUS_IDX, status_table_item
                )
            else:
                status_table_item.setText(file.status)
            # PROGRESS
            progress_bar = self.tblFiles.cellWidget(row, MainWindow.FILE_PROGRESS_IDX)
            if progress_bar is None:
                progress_bar = QProgressBar()
                self.tblFiles.setCellWidget(
                    row, MainWindow.FILE_PROGRESS_IDX, progress_bar
                )
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
                self.__restyleFileProgressBar(
                    row, MainWindow.PROGRESS_BAR_PASSIVE_STYLE
                )

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
            last_event_table_item = self.tblFiles.item(
                row, MainWindow.FILE_LAST_EVENT_IDX
            )
            if last_event_table_item is None:
                last_event_table_item = QTableWidgetItem(last_event_str)
                self.tblFiles.setItem(
                    row, MainWindow.FILE_LAST_EVENT_IDX, last_event_table_item
                )
            else:
                last_event_table_item.setText(last_event_str)

    def update_file(self, file: FileModelDTO):
        """Update the file progress of the given file if the right job is selected"""
        with self.file_table_lock:
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
                    self.__update_file_start_stop_buttons(file.status)

    def show_message(self, title, message):
        """Show a message in a dialog"""
        message_dialog(self, message=message, header=title)

    def job_resumed(self, job_name, status, msg):
        """Show a message that the job has been resumed"""
        idx = self.__get_row_index_of_job(job_name)
        if status == Job.RESUME_STARTING:
            # update the job in the table to resuming state
            self.resuming_jobs.append(job_name)
            item = self.tblJobs.item(idx, MainWindow.JOB_STATUS_IDX)
            if item is not None:
                item.setText("Resuming")
            else:
                self.tblJobs.setItem(
                    idx, MainWindow.JOB_STATUS_IDX, QTableWidgetItem("Resuming")
                )
            return

        if status == Job.RESUME_FAILED:
            self.__show_error_dialog(
                f"""Failed to resume job <b>{job_name}</b>: {msg}. <br/>
                                     You can resume all downloads manually with the 
                                     job start button."""
            )
        # update the job in the table with the db state
        self.__set_job_at_row(idx, self.controller.get_job_dto_by_name(job_name))
        self.resuming_jobs.remove(job_name)
        self.__update_job_toolbar()
        self.__update_file_toolbar()

    def show_crash_report(self, message):
        """Show a crash report in a dialog"""
        CrashReportDialog(message).exec()

    def closeEvent(self, event):
        """Handle the close event (X button) of the window"""
        if self.closing:
            event.accept()
        elif self.close_app():
            event.accept()
        else:
            event.ignore()

    def close_app(self):
        if confirmation_dialog(
            self,
            "Are you sure you want to quit? All downloads will be stopped.",
            "Quit?",
        ):
            self.shutdown_overlay.show()
            self.controller.shutdown()
            self.closing = True
            self.close()
            return True
        else:
            return False

    def pause_all(self):
        if confirmation_dialog(
            self,
            "All jobs will be stopped. Are you sure you want to pause all?",
            "Pause?",
        ):
            self.controller.stop_all_jobs()

    def resume_all(self):
        self.controller.resume_all_jobs()

    def open_settings(self):
        dlg = AppSettingsDialog()
        dlg.exec()
        self.__setup_bandwidth_limit_menu()

    def open_github_page(self):
        QDesktopServices.openUrl(QUrl("https://github.com/kosaendre/aoget/"))
