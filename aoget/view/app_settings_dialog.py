import os
from PyQt6.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from PyQt6 import uic
from PyQt6.QtCore import QDir
from config.app_config import (
    AppConfig,
    set_config_value,
    get_config_value,
    save_config_to_file,
)
from view import ERROR_TEXT_STYLE, DEFAULT_TEXT_STYLE


class AppSettingsDialog(QDialog):
    """Application settings dialog"""

    def __init__(self):
        """Create a new AppSettingsDialog."""
        super(AppSettingsDialog, self).__init__()
        uic.loadUi("aoget/qt/app_settings_dialog.ui", self)
        self.__setup_ui()

    def __setup_ui(self):
        """Set up the UI elements of the dialog."""

        # Set the initial values of the UI elements
        self.btnBrowseTargetFolder.clicked.connect(self.__browse_target_folder)
        job_naming_strategies = [
            "No autonaming",
            "Use webpage title (as seen in the browser window title)",
            "(Recommended) Use URL segment (page for http://example.com/page)",
        ]
        self.cmbJobNaming.addItems(job_naming_strategies)
        self.cmbJobNaming.currentIndexChanged.connect(
            self.__job_naming_strategy_changed
        )
        job_folder_strategies = [
            "(Recommended) Create per-job subfolders using the job's name",
            "Use a shared folder for all jobs",
        ]
        self.cmbJobFolders.addItems(job_folder_strategies)
        self.cmbJobFolders.currentIndexChanged.connect(
            self.__job_folder_strategy_changed
        )

        self.txtTargetFolder.setText(
            get_config_value(AppConfig.DEFAULT_DOWNLOAD_FOLDER)
        )
        self.cmbJobFolders.setCurrentIndex(
            AppConfig.job_folder_strategy_index(
                get_config_value(AppConfig.JOB_SUBFOLDER_POLICY)
            )
        )
        self.cmbJobNaming.setCurrentIndex(
            AppConfig.job_naming_strategy_index(
                get_config_value(AppConfig.JOB_AUTONAMING_PATTERN)
            )
        )
        self.spinHighBandwidth.setValue(
            int(get_config_value(AppConfig.HIGH_BANDWIDTH_LIMIT))
        )
        self.spinHighBandwidth.valueChanged.connect(
            lambda: set_config_value(
                AppConfig.HIGH_BANDWIDTH_LIMIT, self.spinHighBandwidth.value(), True
            )
        )
        self.spinMediumBandwidth.setValue(
            int(get_config_value(AppConfig.MEDIUM_BANDWIDTH_LIMIT))
        )
        self.spinMediumBandwidth.valueChanged.connect(
            lambda: set_config_value(
                AppConfig.MEDIUM_BANDWIDTH_LIMIT,
                self.spinMediumBandwidth.value(),
                True,
            )
        )
        self.spinLowBandwidth.setValue(
            int(get_config_value(AppConfig.LOW_BANDWIDTH_LIMIT))
        )
        self.spinLowBandwidth.valueChanged.connect(
            lambda: set_config_value(
                AppConfig.LOW_BANDWIDTH_LIMIT, str(self.spinLowBandwidth.value()), True
            )
        )
        self.spinThreadsPerJob.setValue(
            int(get_config_value(AppConfig.PER_JOB_DEFAULT_THREAD_COUNT))
        )
        self.spinThreadsPerJob.valueChanged.connect(
            lambda: set_config_value(
                AppConfig.PER_JOB_DEFAULT_THREAD_COUNT,
                self.spinThreadsPerJob.value(),
                True,
            )
        )
        self.chkJobAutoStart.setChecked(get_config_value(AppConfig.AUTO_START_JOBS))
        self.chkJobAutoStart.clicked.connect(
            lambda: set_config_value(
                AppConfig.AUTO_START_JOBS, self.chkJobAutoStart.isChecked(), True
            )
        )
        self.chkOverwriteFiles.setChecked(
            get_config_value(AppConfig.OVERWRITE_EXISTING_FILES)
        )
        self.chkOverwriteFiles.clicked.connect(
            lambda: set_config_value(
                AppConfig.OVERWRITE_EXISTING_FILES,
                self.chkOverwriteFiles.isChecked(),
                True,
            )
        )
        self.chkUrlCaching.setChecked(get_config_value(AppConfig.URL_CACHE_ENABLED))
        self.chkUrlCaching.clicked.connect(
            lambda: set_config_value(
                AppConfig.URL_CACHE_ENABLED, self.chkUrlCaching.isChecked(), True
            )
        )
        self.txtTargetFolder.textChanged.connect(self.__on_target_folder_updated)

    def __on_target_folder_updated(self):
        if not os.path.isabs(self.txtTargetFolder.text()):
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.txtTargetFolder.setStyleSheet(ERROR_TEXT_STYLE)
            self.txtTargetFolder.setToolTip(
                "Default target folder must be a valid, absolute path."
            )
        else:
            self.txtTargetFolder.setStyleSheet(DEFAULT_TEXT_STYLE)
            self.txtTargetFolder.setToolTip("")
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
            set_config_value(
                AppConfig.DEFAULT_DOWNLOAD_FOLDER,
                self.txtTargetFolder.text(),
                save=True
            )

    def __browse_target_folder(self):
        """Open a file dialog to select the target folder."""
        file = str(
            QFileDialog.getExistingDirectory(
                self, caption="Select Directory", directory=self.txtTargetFolder.text()
            )
        )
        file = QDir.toNativeSeparators(file)
        self.txtTargetFolder.setText(file)
        set_config_value(AppConfig.DEFAULT_DOWNLOAD_FOLDER, file)
        save_config_to_file()

    def __job_naming_strategy_changed(self, index: int):
        """Handle the change of the job naming strategy."""
        set_config_value(
            AppConfig.JOB_AUTONAMING_PATTERN, AppConfig.JOB_NAMING_STRATEGY[index]
        )
        save_config_to_file()

    def __job_folder_strategy_changed(self, index: int):
        """Handle the change of the job folder strategy."""
        set_config_value(
            AppConfig.JOB_SUBFOLDER_POLICY, AppConfig.JOB_FOLDER_STRATEGY[index]
        )
        save_config_to_file()
