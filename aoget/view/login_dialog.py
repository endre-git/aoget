import os
import logging
from PyQt6.QtWidgets import QDialog, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEnginePage,
    qWebEngineChromiumVersion,
)
from PyQt6.QtCore import QUrl, Qt
from PyQt6 import uic
from view import DEFAULT_TEXT_STYLE, ERROR_TEXT_STYLE, PROGRESS_BAR_ACTIVE_STYLE
from config.app_config import AppConfig, get_config_value

DEFAULT_LOGIN_URL = "https://archive.org/account/login"
logger = logging.getLogger(__name__)
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--enable-logging --v=1'


class LoginDialog(QDialog):
    """Application settings dialog"""

    def __init__(self):
        """Create a new AppSettingsDialog."""
        super(LoginDialog, self).__init__()
        uic.loadUi("aoget/qt/web_login_dialog.ui", self)
        self.__setup_embedded_browser()
        self.__setup_ui()

    def __setup_embedded_browser(self):
        self.webView = QWebEngineView()
        self.profile = QWebEngineProfile(qWebEngineChromiumVersion())
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        web_cache_path = get_config_value(AppConfig.WEB_CACHE_FOLDER)
        # Specify the directory where cookies will be stored
        self.profile.setCachePath(web_cache_path)
        # left the following line here as a reminder: this doesn't work, bug should be reported
        # web_storage_path = get_config_value(AppConfig.WEB_STORAGE_FOLDER)
        # self.profile.setPersistentStoragePath(web_storage_path)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)

        # Create a QWebEngineView with the profile
        webpage = QWebEnginePage(self.profile, self.webView)
        self.webView.setPage(webpage)

    def __setup_ui(self):
        """Set up the UI elements of the dialog."""

        self.progressPageLoad.setStyleSheet(PROGRESS_BAR_ACTIVE_STYLE)
        self.progressPageLoad.hide()
        self.webView.loadStarted.connect(self.onLoadStarted)
        self.webView.loadProgress.connect(self.onLoadProgress)
        self.webView.loadFinished.connect(self.onLoadFinished)

        self.txtUrl.setText(DEFAULT_LOGIN_URL)
        self.webView.load(QUrl(DEFAULT_LOGIN_URL))
        self.txtUrl.textChanged.connect(self.__on_url_changed)
        self.txtUrl.returnPressed.connect(self.__on_url_enter)

        self.webView.urlChanged.connect(self.__update_url_textbox)

        # add the webview to frameWebview frame
        self.frameWebview.setLayout(QVBoxLayout())
        self.frameWebview.layout().addWidget(self.webView)
        self.btnClose.clicked.connect(self.__on_close_clicked)

    def __on_close_clicked(self):
        self.close()

    def __on_url_changed(self):
        # recolor the text box if the URL changed but enter not yet pressed
        self.txtUrl.setStyleSheet(ERROR_TEXT_STYLE)

    def __on_url_enter(self):
        # if the URL doesn't start with https:// then we prepend it:
        url = self.txtUrl.text()
        if not url.startswith("http"):
            url = "https://" + url
            self.txtUrl.setText(url)
        self.webView.load(QUrl(self.txtUrl.text()))
        self.txtUrl.setStyleSheet(DEFAULT_TEXT_STYLE)

    def __update_url_textbox(self, url: QUrl):
        self.txtUrl.setText(url.toString())
        self.txtUrl.setStyleSheet(DEFAULT_TEXT_STYLE)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def onLoadStarted(self):
        self.progressPageLoad.show()

    def onLoadProgress(self, progress):
        self.progressPageLoad.setValue(progress)

    def onLoadFinished(self, finished):
        self.progressPageLoad.hide()
