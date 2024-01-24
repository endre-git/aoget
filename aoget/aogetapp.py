import sys
import os
from PyQt6.QtWidgets import QApplication

from view.aogetmainwindow import AoGetMainWindow
from util.qt_util import install_catch_all_exception_handler
import logging
from config.app_config import get_config_value, load_config_from_file, AppConfig
from aogetdb import init_db

logger = logging.getLogger(__name__)


def setup_config():
    load_config_from_file("config.json")
    logging.basicConfig(level=logging.INFO 
                       if get_config_value(AppConfig.DEBUG) == "false"
                       else logging.DEBUG)
    suppress_lib_logs()
    url_cache_rel_path = get_config_value(AppConfig.URL_CACHE_FOLDER)
    if not os.path.exists(url_cache_rel_path):
        os.makedirs(url_cache_rel_path)
    os.environ["TLDEXTRACT_CACHE"] = url_cache_rel_path
    logger.info("App config initialized with: " + str(AppConfig.app_config))


def suppress_lib_logs():
    logging.getLogger("tldextract").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PyQt6").setLevel(logging.WARNING)


def setup_db():
    config_db_url = get_config_value(AppConfig.DATABASE_URL)
    if config_db_url is None:
        raise ValueError("No database URL specified in config file.")
    init_db(config_db_url)


setup_config()
setup_db()

logger.info("Working dir: " + os.getcwd())
logger.info("App config initialized with: " + str(AppConfig.app_config))
app = QApplication(sys.argv)
window = AoGetMainWindow()
install_catch_all_exception_handler(window)
app.exec()
