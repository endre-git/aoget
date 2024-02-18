import logging
from PyQt6.QtWidgets import (
    QMainWindow,
)
from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from controller.main_window_controller import MainWindowController

from view.crash_report_dialog import CrashReportDialog
from view.app_settings_dialog import AppSettingsDialog
from view.main_window_jobs import MainWindowJobs
from view.main_window_files import MainWindowFiles
from view.translucent_widget import TranslucentWidget
from util.aogetutil import human_rate
from util.qt_util import (
    confirmation_dialog,
    message_dialog,
)
from config.app_config import AppConfig, get_config_value, get_app_version
from db.aogetdb import AogetDb

from model.dto.job_dto import JobDTO
from model.dto.file_model_dto import FileModelDTO

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window of the application. Note that this is more a controller than a view.
    View was done in Qt Designer and is loaded from a .ui file found under
    aoget/qt/main_window.ui"""

    update_job_signal = pyqtSignal(JobDTO)
    update_file_signal = pyqtSignal(FileModelDTO)
    message_signal = pyqtSignal(str, str)
    job_resumed_signal = pyqtSignal(str, str, str)

    def __init__(self, aoget_db: AogetDb):
        super(MainWindow, self).__init__()
        self.controller = MainWindowController(self, aoget_db)
        uic.loadUi("aoget/qt/main_window.ui", self)
        self.closing = False
        self.jobs_table_view = MainWindowJobs(self)
        self.files_table_view = MainWindowFiles(self)
        self.__setup_ui()
        self.show()
        self.controller.resume_state()

    def __setup_ui(self):
        """Setup the UI"""

        # connect signals
        self.update_job_signal.connect(self.jobs_table_view.update_job)
        self.update_file_signal.connect(self.files_table_view.update_file)
        self.message_signal.connect(self.show_message)
        self.job_resumed_signal.connect(self.jobs_table_view.job_resumed)
        self.actionOpen_GitHub_page.triggered.connect(self.open_github_page)
        self.actionSettings.triggered.connect(self.open_settings)
        self.actionExit.triggered.connect(self.close_app)
        self.actionPause_all.triggered.connect(self.pause_all)
        self.actionResume_all.triggered.connect(self.resume_all)

        self.__setup_bandwidth_limit_menu()
        self.__setup_trivial_menu_items()
        self.jobs_table_view.setup_ui()
        self.jobs_table_view.update_table()
        self.files_table_view.setup_ui()
        self.__setup_overlays()
        self.__on_bandwidth_unlimited()
        self.jobs_table_view.update_job_toolbar()

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

    def __setup_trivial_menu_items(self):
        """Setup the trivial menu items"""
        self.actionAbout.triggered.connect(
            lambda: message_dialog(
                self, message=f"AOGet version is {get_app_version()}", header="About"
            )
        )
        self.actionDonateArchiveOrg.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://archive.org/donate/"))
        )
        self.actionBuy_the_dev_a_Coffee.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://www.buymeacoffee.com/kosaendre")
            )
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

    def show_files(self, job_name):
        """Show the files of the given job in the files table."""
        self.files_table_view.show_files(job_name)

    def update_file_toolbar(self):
        """Update the file toolbar"""
        self.files_table_view.update_file_toolbar()

    def is_job_selected(self):
        """Determine whether a job is selected"""
        return self.jobs_table_view.is_job_selected()

    def is_file_selected(self, filename=None):
        """Determine whether a file is selected"""
        return self.files_table_view.is_file_selected(filename)

    def show_message(self, title, message):
        """Show a message in a dialog"""
        message_dialog(self, message=message, header=title)

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
        QDesktopServices.openUrl(QUrl("https://github.com/endre-git/aoget/"))
