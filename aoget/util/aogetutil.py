import os
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
    """Get a timestamp string in the format YYYYMMDD-HHMMSSmmm.
    :return:
        The timestamp string"""
    return datetime.now().strftime("%Y%m%d-%H%M%S%f")[:-3]


def human_timestamp_from(timestamp_str: str):
    """Get a human readable timestamp from the given timestamp string.
    :param timestamp_str:
        The timestamp string to convert
    :return:
        The human readable timestamp"""
    return datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S%f").strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def human_filesize(file_size_bytes: int) -> str:
    """Get a human readable filesize from the given filesize in bytes.
    :param file_size_bytes:
        The filesize in bytes
    :return:
        The human readable filesize"""
    if (
        not isinstance(file_size_bytes, int)
        or file_size_bytes <= 0
        or file_size_bytes is None
    ):
        return ""
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
    if rate_bytes_per_second is None or rate_bytes_per_second <= 0:
        return ""
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
    if eta_seconds <= 0 or eta_seconds is None:
        return ""
    return str(timedelta(seconds=eta_seconds))


def human_duration(duration_seconds: float) -> str:
    """Get a human readable duration from the given duration as milliseconds, seconds, minutes
    or hours, depending on the length of time.
    :param duration_seconds:
        The duration in seconds
    :return:
        The human readable duration"""
    if duration_seconds is None or duration_seconds <= 0:
        return ""
    if duration_seconds < 1:
        return f"{(duration_seconds * 1000):.3f} milliseconds"
    if duration_seconds < 60:
        return f"{duration_seconds:.1f} seconds"
    if duration_seconds < 3600:
        return f"{(duration_seconds // 60):.1f} minutes"
    return f"{(duration_seconds // 3600):.1f} hours"


def get_last_log_lines(log_file: str, num_lines: int) -> list:
    """Get the last num_lines of the log file.
    :param log_file:
        The log file to get the last lines of
    :param num_lines:
        The number of lines to get
    :return:
        The last num_lines of the log file"""
    if not os.path.exists(log_file):
        return []
    with open(log_file, "r") as file:
        lines = file.readlines()
        return lines[-num_lines:]


def get_crash_report(crash_log_path: str) -> str:
    """Get the crash report from the given crash log file.
    :param crash_log_path:
        The path to the crash log file
    :return:
        The crash report"""
    if not os.path.exists(crash_log_path):
        return None
    # crash log path without file extension
    renamed = os.path.splitext(crash_log_path)[0] + "-" + timestamp_str() + ".html"
    os.rename(crash_log_path, renamed)
    with open(renamed, "r") as file:
        return file.read()
