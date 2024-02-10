import sys
import os

from PyQt6.QtWidgets import QApplication
from view.main_window import MainWindow
from util.qt_util import install_catch_all_exception_handler
import logging
from config.app_config import get_config_value, load_config_from_file, AppConfig, get_app_version
from db.aogetdb import init_db

logger = logging.getLogger(__name__)


def setup_logging():
    # Create a logger
    logger = logging.getLogger()
    level = (
        logging.DEBUG if get_config_value(AppConfig.DEBUG) == "true" else logging.INFO
    )
    logger.setLevel(level)

    # Create a file handler for output file
    file_handler = logging.FileHandler(get_config_value(AppConfig.LOG_FILE_PATH))
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s :: %(levelname)s :: %(name)s:%(lineno)d :: %(message)s'
        )
    )

    # Create a console handler for output to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s :: %(levelname)s :: %(name)s:%(lineno)d :: %(message)s'
        )
    )

    # Add both handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


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
        raise e


def suppress_lib_logs():
    logging.getLogger("tldextract").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PyQt6").setLevel(logging.WARNING)


def setup_db():
    config_db_url = get_config_value(AppConfig.DATABASE_URL)
    if config_db_url is None:
        raise ValueError("No database URL specified in config file.")
    return init_db(config_db_url)


setup_config()
aoget_db = setup_db()

logger.info("App version: " + get_app_version())
logger.info("Working dir: " + os.getcwd())
logger.info("App config initialized with: " + str(AppConfig.app_config))
app = QApplication(sys.argv)

window = MainWindow(aoget_db)
install_catch_all_exception_handler(
    window,
    get_config_value(AppConfig.LOG_FILE_PATH),
    get_config_value(AppConfig.CRASH_LOG_FILE_PATH),
)
app.exec()
