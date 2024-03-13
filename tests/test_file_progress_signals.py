import threading
from unittest.mock import MagicMock

import pytest

from aoget.controller.journal_daemon import JournalDaemon
from aoget.model.dto.job_dto import JobDTO
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.web.queued_downloader import QueuedDownloader
from aoget.web.queued_downloader import FileProgressSignals


@pytest.fixture
def mock_journal_daemon():
    return MagicMock(spec=JournalDaemon)


@pytest.fixture
def job_dto():
    return JobDTO(
        id=1,
        status="test-status",
        page_url="http://example.com",
        name="test_job",
        target_folder="/path/to/download",
        total_size_bytes=0,
    )


@pytest.fixture
def file_model_dto():
    return FileModelDTO(
        name="test_file", job_name="test_job", url="http://example.com/testfile"
    )


@pytest.fixture
def queued_downloader(job_dto, mock_journal_daemon):
    return QueuedDownloader(
        job=job_dto, journal_daemon=mock_journal_daemon, worker_pool_size=1
    )


def test_on_update_progress(mock_journal_daemon):
    jobname = "test_job"
    filename = "test_file"
    written = 100
    total = 200

    signals = FileProgressSignals(jobname, filename, mock_journal_daemon)
    signals.on_update_progress(written, total)

    mock_journal_daemon.update_download_progress.assert_called_once_with(
        jobname, filename, written, total
    )


def test_on_update_status(mock_journal_daemon):
    jobname = "test_job"
    filename = "test_file"
    status = "test_status"
    err = "test_error"

    signals = FileProgressSignals(jobname, filename, mock_journal_daemon)
    signals.on_update_status(status, err)

    mock_journal_daemon.update_file_status.assert_called_once_with(
        jobname, filename, status, err=err
    )


def test_register_status_listener():
    jobname = "test_job"
    filename = "test_file"
    status = "test_status"
    event = threading.Event()

    signals = FileProgressSignals(jobname, filename, MagicMock(spec=JournalDaemon))
    signals.register_status_listener(event, status)

    assert signals.status_listeners[status] == event


def test_on_event(mock_journal_daemon):
    jobname = "test_job"
    filename = "test_file"
    event = "test_event"

    signals = FileProgressSignals(jobname, filename, mock_journal_daemon)
    signals.on_event(event)

    mock_journal_daemon.add_file_event.assert_called_once_with(jobname, filename, event)
