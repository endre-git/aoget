import pytest
import time
from unittest.mock import MagicMock, patch
from aoget.model.dto.job_dto import JobDTO
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.web.queued_downloader import QueuedDownloader
from aoget.controller.journal_daemon import JournalDaemon


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
        name="test_file",
        job_name="test_job",
        url="http://example.com/testfile",
        priority=-1,  # hack: make it lower prio than the poison pill so that it's actually picked up
    )


@pytest.fixture
def queued_downloader(job_dto, mock_journal_daemon):
    return QueuedDownloader(
        job=job_dto, journal_daemon=mock_journal_daemon, worker_pool_size=1
    )


def test_downloader(queued_downloader, file_model_dto):
    with patch('aoget.web.downloader.download_file') as mock_download_file:
        queued_downloader.download_file(file_model_dto)
        queued_downloader.queue.poison_pill()
        queued_downloader.start_download_threads()
        queued_downloader.stop()

        #mock_download_file.assert_called_once()
        #assert mock_download_file.call_args[0][0] == file_model_dto.url
        #assert mock_download_file.call_args[0][1].endswith(file_model_dto.name)


def test_stop_download_threads(queued_downloader):
    queued_downloader.start_download_threads()
    queued_downloader.stop()
    time.sleep(0.1)
    assert not queued_downloader.are_download_threads_running


def test_cancel_download(queued_downloader, file_model_dto):
    queued_downloader.download_file(file_model_dto)
    queued_downloader.cancel_download(file_model_dto.name)
    assert file_model_dto.name not in queued_downloader.files_in_queue


def test_download_files(queued_downloader, file_model_dto):
    queued_downloader.download_files([file_model_dto])
    queued_downloader.queue.poison_pill()
    queued_downloader.start_download_threads()
    queued_downloader.stop()


def test_update_priority(queued_downloader, file_model_dto):
    queued_downloader.download_file(file_model_dto)
    file_model_dto.priority = 1
    queued_downloader.update_priority(file_model_dto)
    assert queued_downloader.queue.pop_file().priority == 1
