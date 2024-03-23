import os
import logging
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import Qt
from PyQt6 import uic
from view.embedded_browser import EmbeddedBrowser

DEFAULT_LOGIN_URL = "https://archive.org/account/login"
logger = logging.getLogger(__name__)
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--enable-logging --v=1'


class LoginDialog(QDialog):
    """Application settings dialog"""

    def __init__(self):
        """Create a new AppSettingsDialog."""
        super(LoginDialog, self).__init__()
        uic.loadUi("aoget/qt/web_login_dialog.ui", self)
        self.__setup_ui()
        self.embedded_browser.load(DEFAULT_LOGIN_URL)

    def __setup_ui(self):
        """Set up the UI elements of the dialog."""
        # add the webview to frameWebview frame
        self.embedded_browser = EmbeddedBrowser()
        self.embedded_browser.add_to_frame(self.frameWebview)
        self.btnClose.clicked.connect(self.__on_close_clicked)

    def __on_close_clicked(self):
        """Close the dialog."""
        self.close()

    def keyPressEvent(self, event):
        """Override the dialog's key press event to ignore Enter key press."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            event.ignore()
        else:
            super().keyPressEvent(event)
