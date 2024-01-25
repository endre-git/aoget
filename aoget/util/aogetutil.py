import urllib.parse
from datetime import datetime
from datetime import timedelta


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


def human_filesize(file_size_bytes: int) -> str:
    """Get a human readable filesize from the given filesize in bytes.
    :param file_size_bytes:
        The filesize in bytes
    :return:
        The human readable filesize"""
    if file_size_bytes == 0:
        return "0B"
    suffixes = ["B", "KB", "MB", "GB", "TB"]
    suffix_index = 0
    while file_size_bytes >= 1024:
        suffix_index += 1
        file_size_bytes /= 1024
    return f"{file_size_bytes:.1f}{suffixes[suffix_index]}"


def human_rate(rate_bytes_per_second: float) -> str:
    """Get a human readable rate from the given rate in bytes per second.
    :param rate_bytes_per_second:
        The rate in bytes per second
    :return:
        The human readable rate"""
    if rate_bytes_per_second == 0:
        return "0B/s"
    suffixes = ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]
    suffix_index = 0
    while rate_bytes_per_second >= 1024:
        suffix_index += 1
        rate_bytes_per_second /= 1024
    return f"{rate_bytes_per_second:.1f}{suffixes[suffix_index]}"


def human_eta(eta_seconds: int) -> str:
    """Get a human readable ETA from the given ETA in seconds in a HH:mm:ss format.
    :param eta_seconds:
        The ETA in seconds
    :return:
        The human readable ETA. For zero time left returns a blank string"""
    if eta_seconds == 0:
        return ""
    return str(timedelta(seconds=eta_seconds))