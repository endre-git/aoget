import os
import json
import logging

logger = logging.getLogger(__name__)

VERSION = "0.9.1"


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
    DEFAULT_DOWNLOAD_FOLDER = "default-download-folder"
    AUTO_START_JOBS = "auto-start-jobs"
    JOB_AUTONAMING_PATTERN = "job-autonaming-pattern"
    JOB_SUBFOLDER_POLICY = "job-subfolder-policy"
    LOW_BANDWIDTH_LIMIT = "low-bandwidth-limit"
    MEDIUM_BANDWIDTH_LIMIT = "medium-bandwidth-limit"
    HIGH_BANDWIDTH_LIMIT = "high-bandwidth-limit"
    OVERWRITE_EXISTING_FILES = "overwrite-existing-files"
    PER_JOB_DEFAULT_THREAD_COUNT = "per-job-default-thread-count"
    URL_CACHE_ENABLED = "url-cache-enabled"
    DOWNLOAD_RETRY_ATTEMPTS = "download-retry-attempts"

    app_config = {}

    defaults = {
        DEBUG: False,
        SETTINGS_FOLDER: "settings",
        TARGET_FOLDER_HISTORY_FILE: "target_folder_history.json",
        URL_HISTORY_FILE: "url_history.json",
        DATABASE_URL: "sqlite:///aoget.db",
        URL_CACHE_FOLDER: "url_cache",
        AUTO_RESOLVE_FILE_SIZES: True,
        LOG_FILE_PATH: "aoget.log",
        CRASH_LOG_FILE_PATH: "crash.log",
        DEFAULT_DOWNLOAD_FOLDER: os.path.join(os.path.expanduser("~"), "Downloads"),
        AUTO_START_JOBS: True,
        JOB_AUTONAMING_PATTERN: "{title}",
        JOB_SUBFOLDER_POLICY: "per-job",
        LOW_BANDWIDTH_LIMIT: 100,
        MEDIUM_BANDWIDTH_LIMIT: 1000,
        HIGH_BANDWIDTH_LIMIT: 5000,
        OVERWRITE_EXISTING_FILES: True,
        PER_JOB_DEFAULT_THREAD_COUNT: 3,
        URL_CACHE_ENABLED: True,
        DOWNLOAD_RETRY_ATTEMPTS: 5,
    }

    JOB_NAMING_STRATEGY = {
        0: "none",
        1: "title",
        2: "url",
    }

    JOB_FOLDER_STRATEGY = {
        0: "per-job",
        1: "shared",
    }

    def job_naming_strategy_index(strategy: str) -> int:
        return list(AppConfig.JOB_NAMING_STRATEGY.values()).index(strategy)

    def job_folder_strategy_index(strategy: str) -> int:
        return list(AppConfig.JOB_FOLDER_STRATEGY.values()).index(strategy)


def get_app_version() -> str:
    return VERSION


def get_config_value(key: str) -> str:
    """Get the value of the given key from the config file.
    :param key:
        The key to get the value for
    :return:
        The value of the key"""
    if key not in AppConfig.app_config:
        return AppConfig.defaults[key]
    return AppConfig.app_config[key]


def set_config_value(key: str, value: any, save: bool = False):
    """Set the value of the given key in the config file.
    :param key:
        The key to set the value for
    :param value:
        The value to set"""
    logger.info(f"Setting config value: '{key}' = '{value}'.")
    AppConfig.app_config[key] = value
    if save:
        save_config_to_file()


def save_config_to_file():
    """Save the current configuration to the config file."""
    config_file = "config.json"
    logger.info(f"Saving config to file: '{config_file}'.")
    with open(config_file, 'w') as file:
        json.dump(AppConfig.app_config, file, indent=4)


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
        validate()
    except FileNotFoundError as e:
        logger.error(f"Config file '{filename}' not found.")
        raise FileNotFoundError(f"Config file '{filename}' not found.") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in config: {e}")
        raise json.JSONDecodeError(
            f"Invalid JSON format in config: {e}"
        ) from e
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise Exception(f"Error loading config: {e}") from e


def validate_bandwidth_config():
    low_bandwidth_limit = get_config_value(AppConfig.LOW_BANDWIDTH_LIMIT)
    if low_bandwidth_limit is None:
        low_bandwidth_limit = 100
        set_config_value(AppConfig.LOW_BANDWIDTH_LIMIT, low_bandwidth_limit)
    if not isinstance(low_bandwidth_limit, int):
        raise ValueError(
            f"Invalid value for {AppConfig.LOW_BANDWIDTH_LIMIT} in the current configuration. Must be a number."
        )

    medium_bandwidth_limit = get_config_value(AppConfig.MEDIUM_BANDWIDTH_LIMIT)
    if medium_bandwidth_limit is None:
        medium_bandwidth_limit = 1000
        set_config_value(AppConfig.MEDIUM_BANDWIDTH_LIMIT, medium_bandwidth_limit)
    if not isinstance(medium_bandwidth_limit, int):
        raise ValueError(
            f"Invalid value for {AppConfig.MEDIUM_BANDWIDTH_LIMIT} in the current configuration. Must be a number."
        )

    high_bandwidth_limit = get_config_value(AppConfig.HIGH_BANDWIDTH_LIMIT)
    if high_bandwidth_limit is None:
        high_bandwidth_limit = 5000
        set_config_value(AppConfig.HIGH_BANDWIDTH_LIMIT, high_bandwidth_limit)
    if not isinstance(high_bandwidth_limit, int):
        raise ValueError(
            f"Invalid value for {AppConfig.HIGH_BANDWIDTH_LIMIT} in the current configuration. Must be a number."
        )

    per_job_default_thread_count = get_config_value(
        AppConfig.PER_JOB_DEFAULT_THREAD_COUNT
    )
    if per_job_default_thread_count is None:
        per_job_default_thread_count = 3
        set_config_value(
            AppConfig.PER_JOB_DEFAULT_THREAD_COUNT, per_job_default_thread_count
        )
    if not isinstance(per_job_default_thread_count, int):
        raise ValueError(
            f"Invalid value for {AppConfig.PER_JOB_DEFAULT_THREAD_COUNT} in the current configuration. Must be a number."
        )


def validate():
    debug = get_config_value(AppConfig.DEBUG)
    if debug is None:
        debug = False
        set_config_value(AppConfig.DEBUG, debug)
    if debug not in [True, False]:
        raise ValueError(
            f"Invalid value for {AppConfig.DEBUG} in the current configuration: {debug} Must be 'true' or 'false'."
        )
    if not os.path.exists(get_config_value(AppConfig.SETTINGS_FOLDER)):
        os.path.mkdirs(get_config_value(AppConfig.SETTINGS_FOLDER))
        logger.info(
            "Created settings folder: " + get_config_value(AppConfig.SETTINGS_FOLDER)
        )
    default_download_folder = get_config_value(AppConfig.DEFAULT_DOWNLOAD_FOLDER)
    if default_download_folder is None or default_download_folder == "":
        # use user home folder
        default_download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        set_config_value(AppConfig.DEFAULT_DOWNLOAD_FOLDER, default_download_folder)
        logger.info("Using default download folder: " + default_download_folder)
    if not os.path.exists(default_download_folder):
        os.makedirs(default_download_folder)
        logger.info("Created default download folder: " + default_download_folder)

    validate_bandwidth_config()

    auto_start_jobs = get_config_value(AppConfig.AUTO_START_JOBS)
    if auto_start_jobs is None:
        auto_start_jobs = True
        set_config_value(AppConfig.AUTO_START_JOBS, auto_start_jobs)

    overwrite_existing_files = get_config_value(AppConfig.OVERWRITE_EXISTING_FILES)
    if overwrite_existing_files is None:
        overwrite_existing_files = True
        set_config_value(AppConfig.OVERWRITE_EXISTING_FILES, overwrite_existing_files)

    url_cache_enabled = get_config_value(AppConfig.URL_CACHE_ENABLED)
    if url_cache_enabled is None:
        url_cache_enabled = True
        set_config_value(AppConfig.URL_CACHE_ENABLED, url_cache_enabled)

    save_config_to_file()  # defaults filled in, let's save it
