"""Module implementing the job editor dialog"""

import logging
from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialog, QFileDialog
from PyQt6 import uic
from PyQt6.QtWidgets import QTreeWidgetItem
from aoget.controller.job_editor_controller import JobEditorController

import aogetsettings

from util.qt_util import error_dialog, qt_debounce, confirmation_dialog

logger = logging.getLogger("NewJobDialog")


class JobEditorDialog(QDialog):
    """Dialog for editing a job. The QT design is defined in aoget/qt/job_editor.ui."""

    def __init__(self, main_window_controller: any):
        super(JobEditorDialog, self).__init__()
        uic.loadUi("aoget/qt/job_editor.ui", self)
        self.app_controller = main_window_controller
        self.__setup_ui()
        self.controller = JobEditorController(self, main_window_controller)
        self.sort_preview_list = True

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
        # filtering on selector tree
        self.txtSelectionFilter.textChanged.connect(
            qt_debounce(self, 500, self.__on_filter_selection_text_changed)
        )

        # browse folder
        self.btnBrowseLocalTarget.clicked.connect(self.__on_browse_folder)

    def __on_browse_folder(self):
        """Button click on browse folder"""
        file = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        aogetsettings.update_target_folder_history(file)
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

    def __on_filter_selection_text_changed(self):
        """Filter the selection based on the text in the filter box"""
        filter_text = self.txtSelectionFilter.text()
        logger.info("Filtering selection: %s.", filter_text)
        for i in range(self.treeFileSelector.topLevelItemCount()):
            extension_node = self.treeFileSelector.topLevelItem(i)
            for j in range(extension_node.childCount()):
                file_node = extension_node.child(j)
                if filter_text in file_node.text(0):
                    file_node.setHidden(False)
                else:
                    file_node.setHidden(True)

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
        else:
            self.lstFilesetPreview.addItem(filename)

    def __remove_from_preview_list(self, filename):
        """Remove the filename from the preview list"""
        for i in range(self.lstFilesetPreview.count()):
            if self.lstFilesetPreview.item(i).text() == filename:
                self.lstFilesetPreview.takeItem(i)
                break

    def __update_preview_list(self):
        """Update the preview list"""
        self.lstFilesetPreview.clear()
        for file in self.job.get_selected_filenames():
            self.lstFilesetPreview.addItem(file)

    def __on_fetch_page(self):
        url = self.cmbPageUrl.currentText()
        try:
            files_by_extension = self.controller.build_fileset(url)
            aogetsettings.update_url_history(url)
            self.lstFilesetPreview.clear()
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
                    child.setFlags(
                        child.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                    )
                    child.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

                    extension_node.addChild(child)
                nodes.append(extension_node)

            self.treeFileSelector.insertTopLevelItems(0, nodes)
            self.treeFileSelector.setEnabled(True)
            self.treeFileSelector.show()
        except Exception as e:
            logger.error(f"Error fetching links from page: {e}")
            error_dialog(self, f"Can't get links from page: {e}")

    def get_job(self):
        """Get the job. The only public method."""
        self.job.target_folder = self.cmbLocalTarget.currentText()
        return self.job
