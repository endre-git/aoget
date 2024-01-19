import urllib.parse
from datetime import datetime


def is_valid_url(url: str) -> bool:
    """Check if the given URL is valid.
    :param url:
        The URL to check
    :return:
        True if the URL is valid, False otherwise"""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def timestamp_str():
    """Get a timestamp string in the format YYYYMMDD-HHMMSS.
    :return:
        The timestamp string"""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def human_timestamp_from(timestamp_str: str):
    """Get a human readable timestamp from the given timestamp string.
    :param timestamp_str:
        The timestamp string to convert
    :return:
        The human readable timestamp"""
    return datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S").strftime(
        "%Y-%m-%d %H:%M:%S"
    )
