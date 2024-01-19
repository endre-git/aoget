import sys
import os
from PyQt6.QtWidgets import QApplication

from view.aogetmainwindow import AoGetMainWindow
import logging

logger = logging.getLogger("aogetapp")
logging.getLogger("aogetapp").setLevel(logging.INFO)

URL_CACHE_REL_PATH = "app_settings/url_cache"
RESULTS_DIR = "app_logs"

logger = logging.getLogger(__name__)


def setup_app():
    if not os.path.exists(URL_CACHE_REL_PATH):
        os.makedirs(URL_CACHE_REL_PATH)
    os.environ["TLDEXTRACT_CACHE"] = URL_CACHE_REL_PATH


setup_app()

logger.info("Working dir: " + os.getcwd())
app = QApplication(sys.argv)

window = AoGetMainWindow()
app.exec()
