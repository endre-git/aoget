
import logging
from config.app_config import get_config_value, AppConfig


def setup_logging():
    # Create a logger
    logger = logging.getLogger()
    level = (
        logging.DEBUG if get_config_value(AppConfig.DEBUG) is True else logging.INFO
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
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
