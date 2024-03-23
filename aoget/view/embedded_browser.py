import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEnginePage,
    qWebEngineChromiumVersion,
)
from PyQt6.QtCore import QUrl
from PyQt6 import uic
from view import DEFAULT_TEXT_STYLE, ERROR_TEXT_STYLE, PROGRESS_BAR_ACTIVE_STYLE
from config.app_config import AppConfig, get_config_value

logger = logging.getLogger(__name__)


class EmbeddedBrowser(QWidget):
    """A class that encapsulates the embedded browser component. This is used to
    display a web page in a dialog. The dialog is assumed to have a progress bar
    that displays page load progress and a text box which sets the URL."""

    def __init__(self):
        """Create a new EmbeddedBrowser."""
        super(EmbeddedBrowser, self).__init__()
        uic.loadUi("aoget/qt/embedded_browser.ui", self)
        self.__setup_web_view()
        self.__setup_text_and_progress()
        self.__setup_ui()

    def __setup_ui(self):
        self.frameWebview.setLayout(QVBoxLayout())
        self.frameWebview.layout().addWidget(self.webView)

    def load(self, url: str = None):
        self.txtUrl.setText(url)
        self.webView.load(QUrl(url))

    def __setup_web_view(self):
        """Setup the browser component"""
        self.webView = QWebEngineView()
        self.profile = QWebEngineProfile(qWebEngineChromiumVersion())
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        logger.info(f"Persistent storage path: {self.profile.persistentStoragePath()}")
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

    def __setup_text_and_progress(self):
        """Wire up the events for the embedded browser."""
        self.progressPageLoad.setStyleSheet(PROGRESS_BAR_ACTIVE_STYLE)
        self.progressPageLoad.hide()
        self.webView.loadStarted.connect(self.onLoadStarted)
        self.webView.loadProgress.connect(self.onLoadProgress)
        self.webView.loadFinished.connect(self.onLoadFinished)

        self.txtUrl.textChanged.connect(self.__on_url_changed)
        self.txtUrl.returnPressed.connect(self.__on_url_enter)

        self.webView.urlChanged.connect(self.__update_url_textbox)

    def __on_url_changed(self):
        """Handle the URL changing in the text box."""
        # recolor the text box if the URL changed but enter not yet pressed
        self.txtUrl.setStyleSheet(ERROR_TEXT_STYLE)

    def __on_url_enter(self):
        """When enter pressed in the URL text box."""
        # if the URL doesn't start with https:// then we prepend it:
        url = self.txtUrl.text()
        if not url.startswith("http"):
            url = "https://" + url
            self.txtUrl.setText(url)
        self.webView.load(QUrl(self.txtUrl.text()))
        self.txtUrl.setStyleSheet(DEFAULT_TEXT_STYLE)

    def __update_url_textbox(self, url: QUrl):
        """Update the URL text box with the current URL coming from the web renderer."""
        self.txtUrl.setText(url.toString())
        self.txtUrl.setStyleSheet(DEFAULT_TEXT_STYLE)

    def get_web_engine_view_component(self):
        """Gets the web engine view component that can be embedded in a dialog."""
        return self.webView

    def onLoadStarted(self):
        self.progressPageLoad.show()

    def onLoadProgress(self, progress):
        self.progressPageLoad.setValue(progress)

    def onLoadFinished(self, finished):
        self.progressPageLoad.hide()

    def create_tight_margin_layout(self):
        """Create a layout with tight margins. This is useful when we want to add the
        browser to a frame with no margins."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def add_to_frame(self, frame):
        """Add the browser to a frame. Typically the embedded browser is added to a frame
        in a dialog. This is a convenience method to do that."""
        frame.setLayout(self.create_tight_margin_layout())
        frame.layout().addWidget(self)
