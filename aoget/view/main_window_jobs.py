import logging

from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem, QFileDialog
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from view.job_editor_dialog import JobEditorDialog
from view.progress_bar_placeholder_widget_item import ProgressBarPlaceholderWidgetItem
from view.progress_bar_widget import ProgressBarWidget
from view.files_widget_item import FilesWidgetItem
from view.threads_widget_item import ThreadsWidgetItem
from view.rate_widget_item import RateWidgetItem
from view.size_widget_item import SizeWidgetItem
from model.job import Job
from model.dto.job_dto import JobDTO

from util.qt_util import (
    confirmation_dialog,
    show_warnings,
    message_dialog,
    error_dialog,
)
from util.aogetutil import human_eta, human_rate, human_filesize
from config.app_config import AppConfig, get_config_value

logger = logging.getLogger(__name__)

JOB_NAME_IDX = 0
JOB_SIZE_IDX = 1
JOB_STATUS_IDX = 2
JOB_RATE_IDX = 3
JOB_THREADS_IDX = 4
JOB_FILES_IDX = 5
JOB_PROGRESS_IDX = 6
JOB_ETA_IDX = 7
JOB_TARGET_FOLDER_IDX = 8


class MainWindowJobs:
    """Artificial extraction of the jobs-related UI controls and related methods from MainWindow.
    A better solution could be to use a Qt component, but that seems incompatible with Qt Designer.
    Signal defs remain in MainWindow but handler methods are in this class. A general pattern used
    in this class is to define mw as the main window object and use it as a handle to access the
    UI objects.
    """

    def __init__(self, main_window):
        """Initialize the MainWindowJobs object.
        :param main_window: The main window object."""
        self.main_window = main_window
        self.resuming_jobs = []

    def setup_ui(self):
        self.__setup_table()

    def __setup_table(self):
        """Setup the jobs table and controls around it"""
        mw = self.main_window
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
        mw.tblJobs.setColumnCount(len(labels))
        mw.tblJobs.setHorizontalHeaderLabels(labels)
        header = mw.tblJobs.horizontalHeader()
        header.setSectionResizeMode(JOB_NAME_IDX, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(JOB_SIZE_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(JOB_STATUS_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(JOB_RATE_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(JOB_THREADS_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(JOB_FILES_IDX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(JOB_PROGRESS_IDX, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            JOB_TARGET_FOLDER_IDX, QHeaderView.ResizeMode.Stretch
        )
        mw.tblJobs.horizontalHeaderItem(JOB_NAME_IDX).setToolTip("Name of the job")
        mw.tblJobs.horizontalHeaderItem(JOB_SIZE_IDX).setToolTip(
            """Total size of the job, calculated from file sizes. If still being resolved,
            will be shown as >X."""
        )
        mw.tblJobs.horizontalHeaderItem(JOB_STATUS_IDX).setToolTip("Status of the job")
        mw.tblJobs.horizontalHeaderItem(JOB_RATE_IDX).setToolTip(
            "Download rate of the job"
        )
        mw.tblJobs.horizontalHeaderItem(JOB_THREADS_IDX).setToolTip(
            "Number of active download threads / allocated download threads"
        )
        mw.tblJobs.horizontalHeaderItem(JOB_FILES_IDX).setToolTip(
            "Number of downloaded files / total files in the job"
        )
        mw.tblJobs.horizontalHeaderItem(JOB_PROGRESS_IDX).setToolTip(
            "Progress of the job based on size, not shown if the size is not fully resolved."
        )
        mw.tblJobs.horizontalHeaderItem(JOB_ETA_IDX).setToolTip(
            """ETA for the job to complete. Not shown if the size is not fully resolved.
            Might be way off with poor server bandwidth."""
        )
        mw.tblJobs.horizontalHeaderItem(JOB_TARGET_FOLDER_IDX).setToolTip(
            "Target folder for the job, where the downloaded files are saved."
        )

        mw.tblJobs.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        mw.tblJobs.setSelectionMode(QHeaderView.SelectionMode.SingleSelection)
        mw.tblJobs.verticalHeader().setHidden(True)
        column_widths = [200, 70, 100, 70, 70, 70, 250, 70, 200]
        for i, width in enumerate(column_widths):
            mw.tblJobs.setColumnWidth(i, width)

        # job control buttons
        mw.btnJobStart.clicked.connect(self.__on_job_start)
        mw.btnJobStop.clicked.connect(self.__on_job_stop)
        mw.btnJobThreadsPlus.clicked.connect(self.__on_job_threads_plus)
        mw.btnJobThreadsMinus.clicked.connect(self.__on_job_threads_minus)
        mw.btnJobCreate.clicked.connect(self.__on_create_new_job)
        mw.btnJobEdit.clicked.connect(self.__on_edit_job)
        mw.btnJobRemoveFromList.clicked.connect(self.__on_job_remove_from_list)
        mw.btnJobRemove.clicked.connect(self.__on_job_remove_from_disk)
        mw.btnJobExport.clicked.connect(self.__on_job_export)
        mw.btnJobImport.clicked.connect(self.__on_job_import)
        mw.btnJobOpenLink.clicked.connect(self.__on_job_open_link)
        mw.btnJobHealthCheck.clicked.connect(self.__on_job_health_check)

        # jobs table selection
        mw.tblJobs.itemSelectionChanged.connect(self.__on_job_selected)

    def update_table(self):
        """Update the jobs table with the current job list."""
        mw = self.main_window
        jobs = mw.controller.jobs.get_job_dtos()
        mw.tblJobs.setRowCount(len(jobs))

        for i, job in enumerate(jobs):
            self.set_job_at_row(i, job)

    def is_job_selected(self):
        """Determine whether a job is selected"""
        mw = self.main_window
        selected = mw.tblJobs.selectedItems()
        return selected is not None and len(selected) > 0

    def get_selected_job_name(self):
        """Return the name of the selected job"""
        mw = self.main_window
        return mw.tblJobs.selectedItems()[0].text() if self.is_job_selected() else None

    def update_job_toolbar(self):
        """Update the job toolbar buttons based on the selected job"""
        mw = self.main_window
        job_name = (
            mw.tblJobs.selectedItems()[0].text() if self.is_job_selected() else None
        )
        if job_name is None or job_name in self.resuming_jobs:
            mw.btnJobStart.setEnabled(False)
            mw.btnJobStop.setEnabled(False)
            mw.btnJobThreadsPlus.setEnabled(False)
            mw.btnJobThreadsMinus.setEnabled(False)
            mw.btnJobCreate.setEnabled(True)
            mw.btnJobEdit.setEnabled(False)
            mw.btnJobRemoveFromList.setEnabled(False)
            mw.btnJobRemove.setEnabled(False)
            mw.btnJobExport.setEnabled(False)
            mw.btnJobImport.setEnabled(True)
            mw.btnJobOpenLink.setEnabled(False)
            mw.btnJobHealthCheck.setEnabled(False)
            if job_name in self.resuming_jobs:
                mw.btnJobStart.setToolTip("Job is being resumed, please wait.")
                mw.btnJobStop.setToolTip("Job is being resumed, please wait.")
        else:
            mw.btnJobCreate.setEnabled(True)
            mw.btnJobEdit.setEnabled(True)
            mw.btnJobExport.setEnabled(True)
            mw.btnJobImport.setEnabled(True)
            mw.btnJobStart.setEnabled(True)
            mw.btnJobStop.setEnabled(True)
            mw.btnJobThreadsPlus.setEnabled(True)
            mw.btnJobThreadsMinus.setEnabled(True)
            mw.btnJobRemoveFromList.setEnabled(True)
            mw.btnJobRemove.setEnabled(True)
            mw.btnJobOpenLink.setEnabled(True)
            mw.btnJobHealthCheck.setEnabled(True)
            mw.btnJobStart.setToolTip("Start / resume downloading all files")
            mw.btnJobStop.setToolTip("Stop downloading all files")

    def __on_job_selected(self):
        """Handle the selection of a job in the jobs table."""
        if not self.is_job_selected():
            return
        mw = self.main_window
        selected_job_name = mw.tblJobs.selectedItems()[0].text()
        self.update_job_toolbar()
        mw.show_files(selected_job_name)
        mw.controller.jobs.job_post_select(selected_job_name)

    def __on_job_start(self):
        """Start the selected job"""
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        mw.controller.jobs.start_job(job_name)

    def __on_job_stop(self):
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        mw.controller.jobs.stop_job(job_name)

    def __on_job_threads_plus(self):
        if not self.is_job_selected():
            return
        mw = self.main_window
        current_job = mw.tblJobs.selectedItems()[0].text()
        mw.controller.jobs.add_thread(current_job)

    def __on_job_threads_minus(self):
        if not self.is_job_selected():
            return
        mw = self.main_window
        current_job = mw.tblJobs.selectedItems()[0].text()
        mw.controller.jobs.remove_thread(current_job)

    def __on_create_new_job(self):
        """Create a new job"""
        mw = self.main_window
        selected_job_name = (
            mw.tblJobs.selectedItems()[0].text() if self.is_job_selected() else None
        )
        dlg = JobEditorDialog(mw.controller)
        val = dlg.exec()
        if val == 1:
            self.update_table()
            newly_selected_job = (
                mw.tblJobs.selectedItems()[0].text() if self.is_job_selected() else None
            )
            if (
                newly_selected_job is not None
                and newly_selected_job != selected_job_name
            ):
                mw.show_files(newly_selected_job)
                mw.controller.jobs.job_post_select(newly_selected_job, is_new=True)
            elif get_config_value(AppConfig.AUTO_START_JOBS):
                mw.controller.jobs.start_job(dlg.controller.job.name)

    def __on_edit_job(self):
        """Edit the selected job"""
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        if mw.controller.jobs.is_job_downloading(job_name):
            error_dialog(
                mw, "Job is running. Please stop all downloads before editing."
            )
            return

        mw.controller.jobs.stop_size_resolver_for_job(job_name)
        dlg = JobEditorDialog(mw.controller, job_name)
        val = dlg.exec()
        if val == 1:
            mw.show_files(job_name)
        mw.controller.jobs.restart_size_resolver_for_job(job_name)

    def __on_job_remove_from_list(self):
        """Remove the selected job from the list"""
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        if confirmation_dialog(
            mw,
            f"""Remove job: <b>{job_name}</b>?
            <p>Running downloads will be stopped.<br>
            Files will not be deleted.</p>""",
        ):
            try:
                messages = mw.controller.jobs.delete_job(job_name)
                if messages:
                    show_warnings(
                        mw, "Removed job with the following warnings:", messages
                    )
                self.update_table()
                # deselect table
                mw.tblJobs.clearSelection()
                mw.show_files(None)
            except Exception as e:
                error_dialog(mw, "Failed to remove job: " + str(e))
                logger.error("Failed to remove job: %s", job_name, exc_info=True)
                logger.exception(e)

    def __on_job_remove_from_disk(self):
        """Remove the selected job from the list and delete the local files"""
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        if confirmation_dialog(
            mw,
            f"""Remove job and delete the corresponding files: <b>{job_name}</b>?
            <p>Running downloads will be stopped.<br>
            Files <b>will</b> be deleted.</p>""",
        ):
            try:
                messages = mw.controller.jobs.delete_job(
                    job_name, delete_from_disk=True
                )
                if messages:
                    show_warnings(
                        mw, "Removed job with the following warnings:", messages
                    )
                self.update_table()
                # deselect table
                mw.tblJobs.clearSelection()
                mw.show_files(None)
            except Exception as e:
                error_dialog(mw, "Failed to remove job: " + str(e))
                logger.error("Failed to remove job: %s", job_name, exc_info=True)
                logger.exception(e)

    def __on_job_export(self):
        """Export the selected job"""
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        job_dto = mw.controller.jobs.get_job_dto_by_name(job_name)
        if job_dto.is_size_not_resolved():
            error_dialog(
                mw,
                """Job size is not fully resolved. Please wait for the job to resolve
                its size before exporting.""",
            )
            return

        file, _ = QFileDialog.getSaveFileName(
            mw, "Export Job", "", "YAML files (*.yaml)"
        )
        if file:
            mw.controller.jobs.export_job(job_name, file)

    def __on_job_import(self):
        """Import a job"""
        mw = self.main_window
        selected_job_name = (
            mw.tblJobs.selectedItems()[0].text() if self.is_job_selected() else None
        )
        file, _ = QFileDialog.getOpenFileName(
            mw, "Import Job", "", "YAML files (*.yaml)"
        )
        if file:
            try:
                job_dto, file_dtos = mw.controller.jobs.import_job(file)
                dlg = JobEditorDialog(
                    mw.controller, job_dto=job_dto, file_dtos=file_dtos
                )
                val = dlg.exec()
                if val == 1:
                    self.update_table()
                    newly_selected_job = (
                        self.tblJobs.selectedItems()[0].text()
                        if self.is_job_selected()
                        else None
                    )
                    if (
                        newly_selected_job is not None
                        and newly_selected_job != selected_job_name
                    ):
                        mw.show_files(newly_selected_job)
                        mw.controller.jobs.job_post_select(
                            newly_selected_job, is_new=True
                        )
                    elif get_config_value(AppConfig.AUTO_START_JOBS):
                        mw.controller.jobs.start_job(dlg.controller.job.name)
            except Exception as e:
                error_dialog(mw, "Failed to import job: " + str(e))
                logger.error("Failed to import job: %s", file, exc_info=True)
                logger.exception(e)

    def __on_job_open_link(self):
        """Open the link of the selected job"""
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        job_dto = mw.controller.jobs.get_job_dto_by_name(job_name)
        if job_dto and job_dto.page_url:
            QDesktopServices.openUrl(QUrl(job_dto.page_url))
        else:
            message_dialog(
                mw,
                "The job doesn't seem to have an associated link.<br/>Perhaps it was imported?",
            )

    def __on_job_health_check(self):
        """Perform a health check on the selected job"""
        if not self.is_job_selected():
            return
        mw = self.main_window
        job_name = mw.tblJobs.selectedItems()[0].text()
        if confirmation_dialog(
            mw,
            f"""Perform an integrity check on the job: <b>{job_name}</b>?<br>
            <p>This will check the status of all files in the job and update their status if
            necessary.<br/>
            Checks will be limited to files for which size is known, are currently not downloading
            and already should be on disk (partially or completely downloaded).</p>
            <p>The process will not check the remote links for availability.
            It will be done in the background, with failing files being updated as the
            process goes.</p>""",
        ):
            mw.controller.jobs.health_check(job_name)

    def set_job_at_row(self, row, job: JobDTO):
        """Set the job at the given row in the jobs table"""
        mw = self.main_window
        mw.tblJobs.setItem(row, JOB_NAME_IDX, QTableWidgetItem(job.name))
        mw.tblJobs.item(row, JOB_NAME_IDX).setToolTip(job.name)
        mw.tblJobs.setItem(row, JOB_SIZE_IDX, SizeWidgetItem(self.__job_size_str(job)))
        mw.tblJobs.setItem(row, JOB_STATUS_IDX, QTableWidgetItem(job.status))
        mw.tblJobs.setItem(
            row,
            JOB_RATE_IDX,
            RateWidgetItem(
                human_rate(job.rate_bytes_per_sec)
                if job.status == Job.STATUS_RUNNING
                else ""
            ),
        )
        mw.tblJobs.setItem(
            row,
            JOB_THREADS_IDX,
            ThreadsWidgetItem(
                f"{job.threads_active or 0}/{job.threads_allocated or 0}"
            ),
        )
        mw.tblJobs.setItem(
            row,
            JOB_FILES_IDX,
            FilesWidgetItem(f"{job.files_done or 0}/{job.selected_files_count or 0}"),
        )
        self.__set_job_progress_item(row, job)
        mw.tblJobs.setItem(
            row,
            JOB_ETA_IDX,
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
        mw.tblJobs.setItem(
            row, JOB_TARGET_FOLDER_IDX, QTableWidgetItem(job.target_folder)
        )
        mw.tblJobs.item(row, JOB_TARGET_FOLDER_IDX).setToolTip(job.target_folder)

    def __set_job_progress_item(self, row, job):
        """Set the progress cell for the given job based on the current state of the job"""
        mw = self.main_window
        if job.is_size_not_resolved():
            if job.size_resolver_status == "Running":
                mw.tblJobs.removeCellWidget(row, JOB_PROGRESS_IDX)
                mw.tblJobs.setItem(
                    row,
                    JOB_PROGRESS_IDX,
                    ProgressBarPlaceholderWidgetItem(
                        f"Resolving file size {job.selected_files_with_known_size}/{job.selected_files_count}"
                    ),
                )
                return
            else:
                mw.tblJobs.setItem(
                    row,
                    JOB_PROGRESS_IDX,
                    ProgressBarPlaceholderWidgetItem("Job size not resolved."),
                )
                return
        if job.total_size_bytes is None or job.total_size_bytes == 0:
            mw.tblJobs.setItem(
                row,
                JOB_PROGRESS_IDX,
                ProgressBarPlaceholderWidgetItem("Unknown size"),
            )
            return

        progress_bar = mw.tblJobs.cellWidget(row, JOB_PROGRESS_IDX)
        if progress_bar is None:
            progress_bar = ProgressBarWidget()
            mw.tblJobs.setCellWidget(row, JOB_PROGRESS_IDX, progress_bar)
        completion = int(100 * (job.downloaded_bytes or 0) / job.total_size_bytes)
        progress_bar.setValue(completion)
        progress_bar.set_active()

    def __job_size_str(self, job):
        """Return the size string for the given job"""
        if job.is_size_not_resolved():
            size = human_filesize(job.total_size_bytes)
            if size != "":
                return ">" + size
            else:
                return ""
        return human_filesize(job.total_size_bytes)

    def update_job(self, job: JobDTO) -> None:
        """Update the job in the table. Called by the cycle ticker."""
        mw = self.main_window
        for row in range(mw.tblJobs.rowCount()):
            if job.name == mw.tblJobs.item(row, JOB_NAME_IDX).text():
                self.set_job_at_row(row, job)
                break

    def job_resumed(self, job_name, status, msg):
        """Show a message that the job has been resumed"""
        mw = self.main_window
        idx = self.__get_row_index_of_job(job_name)
        if status == Job.RESUME_STARTING:
            # update the job in the table to resuming state
            self.resuming_jobs.append(job_name)
            item = mw.tblJobs.item(idx, JOB_STATUS_IDX)
            if item is not None:
                item.setText("Resuming")
            else:
                mw.tblJobs.setItem(idx, JOB_STATUS_IDX, QTableWidgetItem("Resuming"))
            return

        if status == Job.RESUME_FAILED:
            error_dialog(
                mw,
                f"""Failed to resume job <b>{job_name}</b>: {msg}. <br/>
                                     You can resume all downloads manually with the
                                     job start button.""",
            )
        # update the job in the table with the db state
        self.set_job_at_row(idx, mw.controller.jobs.get_job_dto_by_name(job_name))
        self.resuming_jobs.remove(job_name)
        self.update_job_toolbar()
        mw.update_file_toolbar()

    def __get_row_index_of_job(self, job_name: str) -> int:
        """Return the row of the job with the given name"""
        mw = self.main_window
        for row in range(mw.tblJobs.rowCount()):
            if job_name == mw.tblJobs.item(row, JOB_NAME_IDX).text():
                return row
        return None
