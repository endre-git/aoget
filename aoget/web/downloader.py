"""Downloader module for downloading files from the internet. This is the lowest
level implementation of the downloader. It is used by the job downloader to
download files."""

# based on https://gist.github.com/tobiasraabe/58adee67de619ce621464c1a6511d7d9

from abc import ABC, abstractmethod
from pathlib import Path
import hashlib
import logging
import time
import requests
from util.aogetutil import human_filesize
import math

TIMEOUT_SECONDS = 5

logger = logging.getLogger(__name__)
time_ns = time.monotonic_ns()

STATUS_NEW = 'New'
STATUS_DOWNLOADING = 'Downloading'
STATUS_QUEUED = 'In queue'
STATUS_COMPLETED = 'Completed'
STATUS_FAILED = 'Failed'
STATUS_STOPPED = 'Stopped'
STATUS_INVALID = 'Invalid'


class DownloadSignals(ABC):
    """Abstract class for bi-directional signaling. Download progress is sent
    to observers, whereas downloaders can cancel downloads."""

    cancelled = False

    @abstractmethod
    def on_update_progress(self, written: int, total: int) -> None:
        """When the download progress is updated.
        Parameters:
        ----------
        written: int
            Bytes written so far locally.
        total: int
            Size of the remote file."""
        pass

    def on_update_status(self, status: str) -> None:
        """When the status of a file is updated.
        Parameters:
        ----------
        status: str
            The new status of the file"""
        pass

    def on_event(self, event: str) -> None:
        """When an event occurs.
        Parameters:
        ----------
        event: str
            The event that occurred"""
        pass

    def cancel(self) -> None:
        """Cancel the download."""
        self.cancelled = True

    def set_rate_limit(self, rate_limit_bps: int) -> None:
        """Set the rate limit in bytes per second.
        Parameters:
        ----------
        rate_limit_bps: int
            The rate limit in bytes per second."""
        self.rate_limit_bps = rate_limit_bps


def __downloader(
    url: str,
    local_path: str,
    resume_byte_pos: int = None,
    signals: DownloadSignals = None,
) -> str:
    """Download url to disk with possible resumption.
    Parameters
    ----------
    url: str
        Remote resource (file) url
    local_path: str
        Local path where to store the file
    resume_byte_pos: int
        Position of byte from where to resume the download
    progress_observer: ProgressObserver
        Observer for download progress
    """
    # Get size of file
    r = requests.head(url, timeout=TIMEOUT_SECONDS)
    file_size = resolve_remote_file_size(url)

    # Append information to resume download at specific byte position
    # to header
    resume_header = {"Range": f"bytes={resume_byte_pos}-"} if resume_byte_pos else None

    # Establish connection
    r = requests.get(url, stream=True, headers=resume_header, timeout=TIMEOUT_SECONDS)

    # Set configuration
    block_size = 1024
    initial_pos = resume_byte_pos if resume_byte_pos else 0
    mode = "ab" if initial_pos else "wb"
    file = Path(local_path)

    # create folder if it doesn't exist
    file.parent.mkdir(parents=True, exist_ok=True)

    with open(file, mode) as f:
        total = file_size
        written = initial_pos
        for chunk in r.iter_content(8 * block_size):

            f.write(chunk)
            chunk_size = len(chunk)
            written += chunk_size

            if (
                signals
                and signals.rate_limit_bps
                and signals.rate_limit_bps > 0
            ):
                time_to_sleep = chunk_size / signals.rate_limit_bps
                if time_to_sleep <= 1:
                    time.sleep(chunk_size / signals.rate_limit_bps)
                else:
                    # ugly hack, but we need to make sure we emit progress updates each second
                    # for rate calculation and also remain responsive to cancellation, so if
                    # the time to sleep is more than 1 second, we sleep in segments of
                    # <1 seconds
                    cycles = time_to_sleep
                    remaining_time = time_to_sleep
                    for i in range(math.ceil(cycles)):
                        fake_delta = (
                            chunk_size / cycles if cycles > 1 else chunk_size * cycles
                        )
                        fake_written = int(written - chunk_size + (i + 1) * fake_delta)
                        signals.on_update_progress(fake_written, total)
                        if signals.cancelled:
                            logger.info(f"Download cancelled for {file}")
                            return STATUS_STOPPED
                        logger.debug(
                            "Sleeping for %f seconds in cycle %f for %s fakewritten=%d",
                            remaining_time,
                            i,
                            file,
                            fake_written,
                        )
                        time.sleep(min(remaining_time, 1 / cycles))
                        remaining_time -= 1 / cycles
            if signals is not None:
                signals.on_update_progress(written, total)
                if signals.cancelled:
                    logger.debug(f"Download cancelled for {file}")
                    return STATUS_STOPPED

    # there's an unlikely possibility that the file was resumed when already
    # completed, so we emit a completed update progress signal, which might
    # be redundant for proper downloads
    if signals is not None:
        signals.on_update_progress(total, total)
    logger.debug("Downloaded %s", url)
    return STATUS_COMPLETED


def download_file(
    url: str, local_path: str, signals: DownloadSignals = None, file_size: int = -1
) -> str:
    """Execute the correct download operation.
    Depending on the size of the file online and offline, resume the
    download if the file offline is smaller than online.
    Parameters
    ----------
    url: str
        Remote resource (file) url
    local_path: str
        Local path where to store the file
    progress_observer: ProgressObserver
        Observer for download progress
    """
    # Establish connection to header of file
    r = requests.head(url, timeout=TIMEOUT_SECONDS)

    # Get filesize of online and offline file
    if file_size != -1:
        file_size_online = file_size
    else:
        file_size_online = resolve_remote_file_size(url)
    server_resume_supported = r.headers.get("accept-ranges", None) is not None
    logger.debug("Server supports resume for: %s", url)
    file = Path(local_path)

    if file.exists():
        file_size_offline = file.stat().st_size

        if file_size_online != file_size_offline:
            if server_resume_supported:
                # resume download

                logger.debug("Resuming download of %s", url)
                signals.on_event(
                    "Resuming download at "
                    + str(human_filesize(file_size_offline))
                    + "."
                )
                return __downloader(
                    url,
                    local_path,
                    file_size_offline,
                    signals=signals,
                )
            else:
                logger.debug(
                    "Server does not support resume for %s, downloading from scratch.",
                    url,
                )
                signals.on_event("Server does not support resume, restarting download.")
                return __downloader(url, local_path, signals=signals)
        else:
            logger.debug("File %s already downloaded.", url)
            signals.on_event("File was already on disk and complete.")
            signals.on_update_progress(file_size_offline, file_size_offline)
            return STATUS_COMPLETED
    else:
        logger.debug("Downloading %s from scratch.", url)
        return __downloader(url, local_path, signals=signals)


def resolve_remote_file_size(url: str) -> int:
    """Resolve the size of a remote file. Go through redirects if necessary.
    Parameters
    ----------
    url: str
        Remote resource (file) url"""
    r = requests.head(url, timeout=TIMEOUT_SECONDS)
    content_length = int(r.headers.get("content-length", 0))
    logger.debug("Length of %s is %d", url, content_length)
    actual_location = r.headers.get("location", None)
    if content_length == 0 and actual_location is not None:
        logger.debug("Resolving redirect to %s from URL %s", actual_location, url)
        return resolve_remote_file_size(actual_location)
    return content_length


def validate_file(local_path: str, expected_hash: str) -> bool:
    """Validate a given file with its hash if available.
    Parameters
    ----------
    local_path: str
        Local path to the file"""
    file = Path(local_path)

    sha = hashlib.sha256()
    with open(file, "rb") as f:
        while True:
            chunk = f.read(1000 * 1000)  # 1MB so that memory is not exhausted
            if not chunk:
                break
            sha.update(chunk)
    try:
        assert sha.hexdigest() == expected_hash
    except AssertionError:
        logger.debug(
            "Failed validating %s, actual hexdigest=%s expected=%s",
            local_path,
            sha.hexdigest(),
            expected_hash,
        )
        return False
    return True
