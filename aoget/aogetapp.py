import sys
import os
import portalocker

from PyQt6.QtWidgets import QApplication
from view.main_window import MainWindow
from util.catch_all_handler import install_catch_all_exception_handler
from util.qt_util import error_dialog
import logging
from config.app_config import (
    get_config_value,
    load_config_from_file,
    AppConfig,
    get_app_version,
)
from config.log_config import setup_logging
from db.aogetdb import init_db

logger = logging.getLogger(__name__)


def setup_config():
    try:
        load_config_from_file("config.json")
        logging.basicConfig(
            level=(
                logging.INFO
                if get_config_value(AppConfig.DEBUG) == "false"
                else logging.DEBUG
            )
        )
        setup_logging()
        suppress_lib_logs()
        url_cache_rel_path = get_config_value(AppConfig.URL_CACHE_FOLDER)
        if not os.path.exists(url_cache_rel_path):
            os.makedirs(url_cache_rel_path)
        os.environ["TLDEXTRACT_CACHE"] = url_cache_rel_path
        logger.info("App config initialized with: " + str(AppConfig.app_config))
    except Exception as e:
        logger.error("Error initializing app config: " + str(e))
        error_dialog(
            parent=None, message=f"Failed app init: {e}", header="AOGet could not start"
        )
        sys.exit(-1)


def suppress_lib_logs():
    logging.getLogger("tldextract").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PyQt6").setLevel(logging.WARNING)


def setup_db():
    config_db_url = get_config_value(AppConfig.DATABASE_URL)
    if config_db_url is None:
        raise ValueError("No database URL specified in config file.")
    return init_db(config_db_url)


def run_single_instance():
    with open("aoget.lock", "wb") as f:
        try:
            portalocker.lock(f, portalocker.LOCK_EX | portalocker.LOCK_NB)
            setup_config()
            aoget_db = setup_db()

            logger.info("App version: " + get_app_version())
            logger.info("Working dir: " + os.getcwd())
            logger.info("App config initialized with: " + str(AppConfig.app_config))

            window = MainWindow(aoget_db)
            install_catch_all_exception_handler(
                window,
                get_config_value(AppConfig.LOG_FILE_PATH),
                get_config_value(AppConfig.CRASH_LOG_FILE_PATH),
            )
            app.exec()

        except portalocker.LockException:
            error_dialog(
                parent=None,
                message="Another instance of AOGet is already running.",
                header="AOGet could not start"
            )
            sys.exit(-1)


app = QApplication(sys.argv)

run_single_instance()
