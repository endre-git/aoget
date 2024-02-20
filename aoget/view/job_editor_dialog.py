"""Module implementing the job editor dialog"""

import os
import logging
from PyQt6 import QtCore
from PyQt6.QtCore import QDir
from PyQt6.QtWidgets import QDialog, QFileDialog
from PyQt6 import uic
from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtWidgets import QAbstractItemView
from PyQt6.QtWidgets import QDialogButtonBox
from controller.job_editor_controller import JobEditorController
from view.translucent_widget import TranslucentWidget
from model.dto.job_dto import JobDTO
from view import JobEditorMode
from config.app_config import get_config_value, AppConfig
from util.disk_util import to_filesystem_friendly_string

import aogetsettings

from util.qt_util import error_dialog, qt_debounce, confirmation_dialog

logger = logging.getLogger("NewJobDialog")


class FetchPageWorker(QtCore.QThread):
    """Worker thread for fetching a page. This is necessary because fetching a page can take a long time."""

    page_fetched = QtCore.pyqtSignal(dict, str)
    page_fetch_failed = QtCore.pyqtSignal(str, str)

    def __init__(self):
        super(FetchPageWorker, self).__init__()

    def set_args(self, controller: JobEditorController, page_url: str):
        self.controller = controller
        self.page_url = page_url

    def run(self):
        try:
            files_by_extension = self.controller.build_fileset(self.page_url)
            self.page_fetched.emit(files_by_extension, self.page_url)
        except Exception as e:
            logger.error(f"Error fetching links from page: {e}")
            self.page_fetch_failed.emit(self.page_url, str(e))


class JobEditorDialog(QDialog):
    """Dialog for editing a job. The QT design is defined in aoget/qt/job_editor.ui."""

    WARNING_TEXT_STYLE = """
        QLineEdit {
            border: 2px solid #f5ba56;
            background-color: #f5ba56;
        }"""

    WARNING_TEXT_STYLE_IN_COMBO_BOX = """
        QLineEdit {
            border: 1px solid #f5ba56;
            background-color: #f5ba56;
        }"""

    DEFAULT_TEXT_STYLE = """
        QLineEdit {
        }"""

    ERROR_TEXT_STYLE = """
        QLineEdit {
            border: 2px solid #ffaa99;
            background-color: #ffaa99;
        }"""

    def __init__(
        self,
        main_window_controller: any,
        job_name: str = None,
        job_dto: JobDTO = None,
        file_dtos: list = None,
    ):
        super(JobEditorDialog, self).__init__()
        uic.loadUi("aoget/qt/job_editor.ui", self)
        self.job_name_unique = True
        self.app_controller = main_window_controller
        self.mode = JobEditorMode.JOB_NEW
        if job_name is not None:
            self.mode = JobEditorMode.JOB_EDITED
        elif job_dto is not None and file_dtos is not None:
            self.mode = JobEditorMode.JOB_IMPORTED

        self.original_name = job_name
        if self.original_name is None and job_dto:
            self.original_name = job_dto.name
        self.__setup_ui()
        self.controller = JobEditorController(
            self, main_window_controller, mode=self.mode
        )
        self.sort_preview_list = True
        if self.mode == JobEditorMode.JOB_EDITED:
            self.loader_overlay.show()
            self.controller.load_job(job_name)
            self.sort_preview_list = False
            self.__populate()
            self.sort_preview_list = True
            self.loader_overlay.hide()
        elif self.mode == JobEditorMode.JOB_IMPORTED:
            self.controller.job = job_dto
            self.controller.use_files(file_dtos)
            self.__populate()
            self.cmbLocalTarget.lineEdit().setText(
                get_config_value(AppConfig.DEFAULT_DOWNLOAD_FOLDER)
            )
        else:
            self.__disable_selector_buttons()
            self.cmbLocalTarget.lineEdit().setText(
                get_config_value(AppConfig.DEFAULT_DOWNLOAD_FOLDER)
            )
        self.__update_ok_status()

        self.naming_strategy = get_config_value(AppConfig.JOB_AUTONAMING_PATTERN)
        self.folder_strategy = get_config_value(AppConfig.JOB_SUBFOLDER_POLICY)

    def __setup_ui(self):
        """Setup the component post generation. This is called from the constructor."""
        # load previously used values from config into combo boxes
        url_history = aogetsettings.get_url_history()
        self.cmbPageUrl.addItem("")
        self.cmbPageUrl.addItems(url_history)

        target_folder_history = aogetsettings.get_target_folder_history()
        self.cmbLocalTarget.addItems(target_folder_history)

        # fetch page button
        self.btnFetchPage.clicked.connect(self.__on_fetch_page)

        # file selector tree check changed
        self.treeFileSelector.itemChanged.connect(
            self.__on_file_selector_tree_check_changed
        )
        # buttons next to selector tree
        self.btnCheckAllShown.clicked.connect(self.__on_check_all_shown)
        self.btnUncheckAllShown.clicked.connect(self.__on_uncheck_all_shown)
        self.btnResetSelection.clicked.connect(self.__on_reset_selection)
        self.btnDeselectDiskDuplicates.clicked.connect(
            self.__on_deselect_disk_duplicates
        )
        self.btnDeselectJobDuplicates.clicked.connect(self.__on_deselect_job_duplicates)
        # filtering on selector tree
        self.txtSelectionFilter.textChanged.connect(
            qt_debounce(self, 500, self.__on_filter_selection_text_changed)
        )
        # filtering on preview list
        self.txtPreviewFilter.textChanged.connect(
            qt_debounce(self, 500, self.__on_filter_preview_text_changed)
        )
        # editing the name
        self.txtJobName.textChanged.connect(self.__on_job_name_text_changed)

        # browse folder
        self.cmbLocalTarget.currentTextChanged.connect(self.__update_target_folder)
        self.btnBrowseLocalTarget.clicked.connect(self.__on_browse_folder)

        # set placeholder texts for combo boxes (not possible from Qt Designer)
        self.cmbPageUrl.lineEdit().setPlaceholderText("Enter or paste URL")
        self.cmbLocalTarget.lineEdit().setPlaceholderText("Select target folder")

        self.lstFilesetPreview.keyPressEvent = self.__on_preview_list_key_press
        self.lstFilesetPreview.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.fetch_page_worker = FetchPageWorker()

        self.fetch_page_worker.page_fetched.connect(self.__on_fetch_page_finished)
        self.fetch_page_worker.page_fetch_failed.connect(self.__on_fetch_page_failed)

        self.loader_overlay = TranslucentWidget(
            self,
            (
                "Loading..."
                if self.mode in [JobEditorMode.JOB_EDITED, JobEditorMode.JOB_IMPORTED]
                else "Fetching links..."
            ),
        )
        self.loader_overlay.resize(self.width(), self.height())
        self.loader_overlay.hide()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(
            self.__on_ok_clicked
        )

    def __on_browse_folder(self):
        """Button click on browse folder"""
        file = str(
            QFileDialog.getExistingDirectory(
                self,
                caption="Select Directory",
                directory=self.cmbLocalTarget.currentText(),
            )
        )
        file = QDir.toNativeSeparators(file)
        self.cmbLocalTarget.setItemText(self.cmbLocalTarget.currentIndex(), file)

    def __on_check_all_shown(self):
        """Button click on check all shown"""
        if self.lstFilesetPreview.count() == 0:
            self.sort_preview_list = False
        for i in range(self.treeFileSelector.topLevelItemCount()):
            extension_node = self.treeFileSelector.topLevelItem(i)
            if not extension_node.isExpanded():
                continue
            for j in range(extension_node.childCount()):
                file_node = extension_node.child(j)
                if not file_node.isHidden():
                    file_node.setCheckState(0, QtCore.Qt.CheckState.Checked)
        self.sort_preview_list = True

    def __on_uncheck_all_shown(self):
        """Button click on uncheck all shown"""
        for i in range(self.treeFileSelector.topLevelItemCount()):
            extension_node = self.treeFileSelector.topLevelItem(i)
            if not extension_node.isExpanded():
                continue
            for j in range(extension_node.childCount()):
                file_node = extension_node.child(j)
                if not file_node.isHidden():
                    file_node.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

    def __on_reset_selection(self):
        """Button click on reset selection"""
        if confirmation_dialog(
            self,
            "Are you sure you want to reset the selection?",
            "Reset selection",
        ):
            self.txtSelectionFilter.clear()
            self.lstFilesetPreview.clear()
            for i in range(self.treeFileSelector.topLevelItemCount()):
                extension_node = self.treeFileSelector.topLevelItem(i)
                for j in range(extension_node.childCount()):
                    file_node = extension_node.child(j)
                    file_node.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

    def __deselect_these(self, filenames):
        """Deselect the given filenames"""
        for i in range(self.treeFileSelector.topLevelItemCount()):
            extension_node = self.treeFileSelector.topLevelItem(i)
            for j in range(extension_node.childCount()):
                file_node = extension_node.child(j)
                if file_node.text(0) in filenames:
                    file_node.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

    def __on_deselect_disk_duplicates(self):
        """Button click on deselect disk duplicates"""
        filenames_in_job_folders = self.controller.all_files_in_job_folders()
        self.__deselect_these(filenames_in_job_folders)

    def __on_deselect_job_duplicates(self):
        """Button click on deselect job duplicates"""
        filenames_in_jobs = self.controller.all_files_in_jobs()
        self.__deselect_these(filenames_in_jobs)

    def __on_filter_selection_text_changed(self):
        """Filter the selection based on the text in the filter box"""
        filter_text = self.txtSelectionFilter.text()
        if filter_text:
            # Set background color to green if there's text
            self.txtSelectionFilter.setStyleSheet(JobEditorDialog.WARNING_TEXT_STYLE)
        else:
            # Reset to default style (or set a different color) if text is empty
            self.txtSelectionFilter.setStyleSheet(JobEditorDialog.DEFAULT_TEXT_STYLE)
        for i in range(self.treeFileSelector.topLevelItemCount()):
            extension_node = self.treeFileSelector.topLevelItem(i)
            for j in range(extension_node.childCount()):
                file_node = extension_node.child(j)
                if filter_text in file_node.text(0):
                    file_node.setHidden(False)
                else:
                    file_node.setHidden(True)

    def __on_filter_preview_text_changed(self):
        """Filter the preview list based on the text in the filter box"""
        filter_text = self.txtPreviewFilter.text()
        if filter_text:
            # Set background color to green if there's text
            self.txtPreviewFilter.setStyleSheet(JobEditorDialog.WARNING_TEXT_STYLE)
        else:
            # Reset to default style (or set a different color) if text is empty
            self.txtPreviewFilter.setStyleSheet(JobEditorDialog.DEFAULT_TEXT_STYLE)
        for i in range(self.lstFilesetPreview.count()):
            item = self.lstFilesetPreview.item(i)
            if filter_text in item.text():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def __on_job_name_text_changed(self):
        """When the job name is changed"""
        job_name = self.txtJobName.text()
        if (
            self.mode == JobEditorMode.JOB_EDITED and job_name == self.original_name
        ) or not self.app_controller.jobs.job_exists(job_name):
            self.txtJobName.setStyleSheet(JobEditorDialog.DEFAULT_TEXT_STYLE)
            self.txtJobName.setToolTip("")
            self.job_name_unique = True
        else:
            self.txtJobName.setStyleSheet(JobEditorDialog.ERROR_TEXT_STYLE)
            self.txtJobName.setToolTip("A job with this name already exists.")
            self.job_name_unique = False

        self.__update_ok_status()

    def __update_ok_status(self):
        """Update the status of the OK button"""
        has_target_folder = self.cmbLocalTarget.currentText() != ""
        target_folder_is_absolute = os.path.isabs(self.cmbLocalTarget.currentText())
        has_job_name = self.txtJobName.text() != ""
        has_page_url = self.cmbPageUrl.currentText() != ""
        if (
            has_page_url
            and has_job_name
            and self.job_name_unique
            and has_target_folder
            and target_folder_is_absolute
        ):
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        else:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def __on_file_selector_tree_check_changed(self, item, column):
        """When an item changed in the file selector tree"""
        if item.checkState(column) == QtCore.Qt.CheckState.Checked:
            self.controller.set_file_selected(item.text(column))
            self.__add_to_preview_list(item.text(column))
        elif item.checkState(column) == QtCore.Qt.CheckState.Unchecked:
            self.controller.set_file_unselected(item.text(column))
            self.__remove_from_preview_list(item.text(column))
        else:
            logger.error("Partially checked" + item.text(column))

    def __add_to_preview_list(self, filename):
        """Add the filename to the preview list, at its alphabetically correct place"""
        if self.sort_preview_list:
            index = 0
            while (
                index < self.lstFilesetPreview.count()
                and filename.lower() > self.lstFilesetPreview.item(index).text().lower()
            ):
                index += 1
            self.lstFilesetPreview.insertItem(index, filename)
            new_item = self.lstFilesetPreview.item(index)
        else:
            self.lstFilesetPreview.addItem(filename)
            new_item = self.lstFilesetPreview.item(self.lstFilesetPreview.count() - 1)

        if (
            self.txtPreviewFilter.text() != ""
            and self.txtPreviewFilter.text() not in filename
        ):
            new_item.setHidden(True)

    def __on_preview_list_key_press(self, event):
        """When a key is pressed on the preview list"""
        if event.key() == QtCore.Qt.Key.Key_Delete:
            for item in self.lstFilesetPreview.selectedItems():
                self.__remove_from_preview_list(item.text())
                # iterate over the tree nodes and uncheck the corresponding file nodes
                for i in range(self.treeFileSelector.topLevelItemCount()):
                    extension_node = self.treeFileSelector.topLevelItem(i)
                    for j in range(extension_node.childCount()):
                        file_node = extension_node.child(j)
                        if file_node.text(0) == item.text():
                            file_node.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                            break
                self.controller.set_file_unselected(item.text())
            event.accept()
        else:
            event.ignore()

    def __remove_from_preview_list(self, filename):
        """Remove the filename from the preview list"""
        for i in range(self.lstFilesetPreview.count()):
            if self.lstFilesetPreview.item(i).text() == filename:
                self.lstFilesetPreview.takeItem(i)
                break

    def __on_fetch_page(self):
        url = self.cmbPageUrl.currentText()
        if not url:
            error_dialog(self, "Please enter a URL.")
            return
        if self.lstFilesetPreview.count() > 0 and not confirmation_dialog(
            self,
            "This will reset the current link set and remove all your selections. Continue?",
            "Please confirm",
        ):
            return
        self.fetch_page_worker.set_args(self.controller, url)
        self.__to_loading_state()
        self.fetch_page_worker.start()

    def __on_fetch_page_finished(self, files_by_extension, url):
        """When the page has been fetched successfully."""
        aogetsettings.update_url_history(url)
        self.lstFilesetPreview.clear()
        self.treeFileSelector.clear()
        nodes = []
        sorted_extensions = sorted(files_by_extension.keys())
        for extension in sorted_extensions:
            if extension == "":
                displayed_extension = "(blank)"
            else:
                displayed_extension = extension
            extension_node = QTreeWidgetItem([displayed_extension])
            for file in files_by_extension[extension]:
                child = QTreeWidgetItem([file.name])
                child.setFlags(child.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                # unchecked by default but if not set explicitly, checkbox won't be shown
                child.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                extension_node.addChild(child)
            nodes.append(extension_node)

        self.treeFileSelector.insertTopLevelItems(0, nodes)
        self.treeFileSelector.setEnabled(True)
        self.treeFileSelector.show()
        self.__on_filter_selection_text_changed()
        name = ""
        if self.naming_strategy == "title":
            name = self.controller.get_page_title()
        elif self.naming_strategy == "url":
            page_url = self.cmbPageUrl.currentText()
            name = page_url.split("/")[-1]
        self.txtJobName.setText(name)

        target_folder = self.cmbLocalTarget.currentText()
        if self.folder_strategy == "per-job" and len(target_folder) > 0 and name != "":
            target_folder = os.path.join(
                target_folder, to_filesystem_friendly_string(name)
            )
        self.cmbLocalTarget.setCurrentText(target_folder)

        self.__update_target_folder()
        self.__to_normal_state()
        self.__enable_selector_buttons()

    def __on_fetch_page_failed(self, url, error_message):
        error_dialog(self, f"Error fetching page {url}: {error_message}")
        self.__to_normal_state()

    def __update_target_folder(self):
        """Update the target folder based on the current values of the form."""
        currentText = self.cmbLocalTarget.currentText()
        if currentText == "":
            self.cmbLocalTarget.lineEdit().setStyleSheet(
                JobEditorDialog.ERROR_TEXT_STYLE
            )
            self.cmbLocalTarget.setToolTip("Please select a target folder.")
        elif not os.path.isabs(currentText):
            self.cmbLocalTarget.lineEdit().setStyleSheet(
                JobEditorDialog.ERROR_TEXT_STYLE
            )
            self.cmbLocalTarget.setToolTip("Please use a valid absolute path.")
        elif (
            self.mode == JobEditorMode.JOB_EDITED
            and self.cmbLocalTarget.currentText() != self.controller.job.target_folder
            and not self.controller.is_new_job()
        ):
            self.cmbLocalTarget.lineEdit().setStyleSheet(
                JobEditorDialog.WARNING_TEXT_STYLE_IN_COMBO_BOX
            )
            self.cmbLocalTarget.setToolTip(
                """Changing the folder of a partially completed job is not recommended.
Downloaded files will fail the consistency check. Partially downloaded files will be restarted."""
            )
        else:
            self.cmbLocalTarget.lineEdit().setStyleSheet(
                JobEditorDialog.DEFAULT_TEXT_STYLE
            )
            self.cmbLocalTarget.setToolTip("")
        self.__update_ok_status()

    def __to_loading_state(self):
        """Switch the UI to the loading state"""
        self.treeFileSelector.setEnabled(False)
        # create a loader overlay on treeFileSelector
        self.treeFileSelector.hide()
        self.loader_overlay.show()
        self.btnFetchPage.setEnabled(False)

    def __to_normal_state(self):
        """Switch the UI to the normal state"""
        self.treeFileSelector.setEnabled(True)
        self.loader_overlay.hide()
        self.treeFileSelector.show()
        if self.mode == JobEditorMode.JOB_NEW:
            self.btnFetchPage.setEnabled(True)

    def __populate(self):
        """Populate the form with the given job. Invoked in editor / import mode."""
        job = self.controller.job
        self.txtJobName.setText(job.name)
        self.cmbPageUrl.setCurrentText(job.page_url)
        self.cmbLocalTarget.setCurrentText(job.target_folder)
        self.cmbPageUrl.setEnabled(False)
        self.cmbPageUrl.setToolTip(
            "Can't change for an existing job. Please create a new job."
        )
        self.btnFetchPage.setEnabled(False)
        self.btnFetchPage.setToolTip(
            "Can't re-fetch for an existing job. Please create a new job."
        )
        self.__load_files()

    def __load_files(self):
        """Load the files from the job into the file selector tree. Invoked only in editor mode."""
        sorted_extensions = sorted(self.controller.files_by_extension.keys())
        nodes = []
        for extension in sorted_extensions:
            if extension == "":
                displayed_extension = "(blank)"
            else:
                displayed_extension = extension
            extension_node = QTreeWidgetItem([displayed_extension])
            for file in self.controller.files_by_extension[extension]:
                child = QTreeWidgetItem([file.name])
                child.setFlags(child.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                # unchecked by default but if not set explicitly, checkbox won't be shown
                if file.selected:
                    child.setCheckState(0, QtCore.Qt.CheckState.Checked)
                    self.__add_to_preview_list(file.name)
                else:
                    child.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                extension_node.addChild(child)
            nodes.append(extension_node)

        self.treeFileSelector.insertTopLevelItems(0, nodes)
        self.treeFileSelector.setEnabled(True)
        self.treeFileSelector.show()

    def __disable_selector_buttons(self):
        """Disable the buttons next to the selector tree"""
        self.btnCheckAllShown.setEnabled(False)
        self.btnUncheckAllShown.setEnabled(False)
        self.btnResetSelection.setEnabled(False)
        self.btnDeselectDiskDuplicates.setEnabled(False)
        self.btnDeselectJobDuplicates.setEnabled(False)

    def __enable_selector_buttons(self):
        """Enable the buttons next to the selector tree"""
        self.btnCheckAllShown.setEnabled(True)
        self.btnUncheckAllShown.setEnabled(True)
        self.btnResetSelection.setEnabled(True)
        self.btnDeselectDiskDuplicates.setEnabled(True)
        self.btnDeselectJobDuplicates.setEnabled(True)

    def __on_ok_clicked(self):
        """When the OK button is clicked"""
        if not self.job_name_unique:
            error_dialog(self, "The job name is not unique.")
            return
        if self.cmbLocalTarget.currentText() == "":
            error_dialog(self, "Please select a target folder.")
            return
        if (
            self.mode == JobEditorMode.JOB_EDITED
            and self.cmbLocalTarget.currentText() != self.controller.job.target_folder
            and not self.controller.is_new_job()
        ):
            if not confirmation_dialog(
                self,
                """Changing the folder of a partially completed job is <b>not recommended</b>.<br>
                    Downloaded files will fail the consistency check.<br>
                    Partially downloaded files will be restarted.<br>
                    The issue can be resolved by moving the files manually.<br>
                    <br>
                    Are you sure you want to continue?""",
            ):
                return
        self.controller.build_job()
        target_folder = self.cmbLocalTarget.currentText()
        self.controller.job.target_folder = target_folder
        self.controller.job.name = self.txtJobName.text()
        aogetsettings.update_target_folder_history(target_folder)
        self.accept()

    def get_job_name(self) -> str:
        """Get the name of the job"""
        return self.txtJobName.text()

    def get_target_folder(self) -> str:
        """Get the target folder"""
        return self.cmbLocalTarget.currentText()
