"""Downloader module for downloading files from the internet. This is the lowest
level implementation of the downloader. It is used by the job downloader to
download files."""
# based on https://gist.github.com/tobiasraabe/58adee67de619ce621464c1a6511d7d9

from abc import ABC, abstractmethod
from pathlib import Path
import hashlib
import logging
import requests

TIMEOUT_SECONDS = 5

logger = logging.getLogger(__name__)


class ProgressObserver(ABC):
    """Abstract class for download progress observers."""

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


def __downloader(
    url: str,
    local_path: str,
    resume_byte_pos: int = None,
    progress_observer: ProgressObserver = None,
) -> None:
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

    with open(file, mode) as f:
        total = file_size
        written = initial_pos
        for chunk in r.iter_content(32 * block_size):
            f.write(chunk)
            written += len(chunk)
            if progress_observer is not None:
                progress_observer.on_update_progress(written, total)


def download_file(
    url: str, local_path: str, progress_observer: ProgressObserver = None
) -> None:
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
    file_size_online = resolve_remote_file_size(url)
    server_resume_supported = r.headers.get("accept-ranges", None) is not None
    logger.info("Server supports resume for: %s", url)
    file = Path(local_path)

    if file.exists():
        file_size_offline = file.stat().st_size

        if file_size_online != file_size_offline:
            if server_resume_supported:
                # resume download
                logger.info("Resuming download of %s", url)
                __downloader(
                    url,
                    local_path,
                    file_size_offline,
                    progress_observer=progress_observer,
                )
            else:
                logger.info(
                    "Server does not support resume for %s, downloading from scratch.",
                    url,
                )
                __downloader(url, local_path, progress_observer=progress_observer)
        else:
            logger.info("File %s already downloaded.", url)
    else:
        logger.info("Downloading %s from scratch.", url)
        __downloader(url, local_path, progress_observer=progress_observer)


def resolve_remote_file_size(url: str) -> int:
    """Resolve the size of a remote file. Go through redirects if necessary.
    Parameters
    ----------
    url: str
        Remote resource (file) url"""
    r = requests.head(url, timeout=TIMEOUT_SECONDS)
    content_length = int(r.headers.get("content-length", 0))
    logger.info("Length of %s is %d", url, content_length)
    actual_location = r.headers.get("location", None)
    if content_length == 0 and actual_location is not None:
        logger.info("Resolving redirect to %s from URL %s", actual_location, url)
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
        logger.info(
            "Failed validating %s, actual hexdigest=%s expected=%s",
            local_path,
            sha.hexdigest(),
            expected_hash,
        )
        return False
    return True
