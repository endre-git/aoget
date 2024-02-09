import json
import logging

logger = logging.getLogger(__name__)

VERSION = "0.9.0"


class AppConfig:
    DEBUG = "debug"
    SETTINGS_FOLDER = "settings-folder"
    TARGET_FOLDER_HISTORY_FILE = "target-folder-history-file"
    URL_HISTORY_FILE = "url-history-file"
    DATABASE_URL = "database-url"
    URL_CACHE_FOLDER = "url-cache-folder"
    AUTO_RESOLVE_FILE_SIZES = "auto-resolve-file-sizes"
    LOG_FILE_PATH = "log-file-path"
    CRASH_LOG_FILE_PATH = "crash-log-file-path"
    app_config = {}


def get_app_version() -> str:
    return VERSION


def get_config_value(key: str) -> str:
    """Get the value of the given key from the config file.
    :param key:
        The key to get the value for
    :return:
        The value of the key"""
    return AppConfig.app_config[key]


def load_config_from_file(filename: str) -> dict:
    """Initialize configuration from the provided config file.
    :param filename:
        The path to the config file
    """
    logger.info(f"Loading config from file: '{filename}'.")
    try:
        with open(filename, 'r') as config_file:
            app_config = json.load(config_file)
            AppConfig.app_config = app_config
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Config file '{filename}' not found.") from e
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON format in config file '{filename}'."
        ) from e
