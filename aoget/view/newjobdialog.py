"""Module implementing the job editor dialog"""

import logging
from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialog, QFileDialog
from PyQt6 import uic
from scrapy.crawler import CrawlerProcess
from PyQt6.QtWidgets import QTreeWidgetItem

import aogetsettings
from model.job import Job
from web.aospider import AoSpider
from web.aopage import AoPage
from util.aogetutil import is_valid_url
from util.qt_util import error_dialog, qt_debounce

logger = logging.getLogger("NewJobDialog")


class NewJobDialog(QDialog):
    """New job dialog. Note that this is more a controller than a view. View was done in
    Qt Designer and is loaded from a .ui file found under aoget/qt/new_job.ui"""

    job = None

    def __init__(self):
        super(NewJobDialog, self).__init__()
        uic.loadUi("aoget/qt/new_job.ui", self)
        self.__setup_ui()
        self.job = Job()

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
        for i in range(self.treeFileSelector.topLevelItemCount()):
            extension_node = self.treeFileSelector.topLevelItem(i)
            for j in range(extension_node.childCount()):
                file_node = extension_node.child(j)
                if not file_node.isHidden():
                    self.job.set_file_selected(file_node.text(0))
                    file_node.setCheckState(0, QtCore.Qt.CheckState.Checked)
        self.__update_preview_list()

    def __on_uncheck_all_shown(self):
        """Button click on uncheck all shown"""
        for i in range(self.treeFileSelector.topLevelItemCount()):
            extension_node = self.treeFileSelector.topLevelItem(i)
            for j in range(extension_node.childCount()):
                file_node = extension_node.child(j)
                if not file_node.isHidden():
                    self.job.set_file_unselected(file_node.text(0))
                    file_node.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
        self.__update_preview_list()

    def __on_reset_selection(self):
        """Button click on reset selection"""
        pass

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
        logger.info(
            "Item check changed: %s %s", item.text(column), str(item.checkState(column))
        )
        if item.checkState(column) == QtCore.Qt.CheckState.Checked:
            self.job.set_file_selected(item.text(column))
        elif item.checkState(column) == QtCore.Qt.CheckState.Unchecked:
            self.job.set_file_unselected(item.text(column))
        else:
            logger.info("Partially checked")
        self.__update_preview_list()

    def __update_preview_list(self):
        """Update the preview list"""
        self.lstFilesetPreview.clear()
        for file in self.job.get_selected_filenames():
            self.lstFilesetPreview.addItem(file)

    def __on_fetch_page(self):
        """Fetch the page and update the preview list"""

        base_url = self.cmbPageUrl.currentText()

        if not is_valid_url(base_url):
            error_dialog(
                self,
                "Invalid URL. Please enter a complete url, including http:// or https://",
            )
            return

        aogetsettings.update_url_history(base_url)
        job_name = base_url.split("/")[-1]
        self.txtJobName.setText(job_name)
        self.job.name = job_name
        self.job.page_url = base_url
        self.job.status = Job.STATUS_CREATED

        logger.info("Fetching page: %s", base_url)
        process = CrawlerProcess(
            settings={
                "FEEDS": {
                    "items.json": {"format": "json"},
                },
                "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
                "HTTPCACHE_ENABLED": False,
            }
        )

        ao_page = AoPage()
        process.crawl(AoSpider, [base_url, ao_page])
        process.start()  # the script will block here until the crawling is finished

        self.job.ingest_links(ao_page)

        nodes = []
        for extension in self.job.file_set.get_sorted_extensions():
            if extension == "":
                displayed_extension = "(blank)"
            else:
                displayed_extension = extension
            extension_node = QTreeWidgetItem([displayed_extension])
            for file in self.job.file_set.get_sorted_filenames_by_extension(extension):
                child = QTreeWidgetItem([file])
                child.setFlags(child.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, QtCore.Qt.CheckState.Unchecked)

                extension_node.addChild(child)
            nodes.append(extension_node)

        self.treeFileSelector.insertTopLevelItems(0, nodes)
        self.treeFileSelector.setEnabled(True)
        self.treeFileSelector.show()

    def get_job(self):
        """Get the job. The only public method."""
        return self.job
