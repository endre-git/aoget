import pytest
import time
from unittest.mock import MagicMock, patch
from aoget.model.dto.job_dto import JobDTO
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.web.queued_downloader import QueuedDownloader
from aoget.web.journal_daemon import JournalDaemon
import aoget

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
        total_size_bytes=0
    )


@pytest.fixture
def file_model_dto():
    return FileModelDTO(name="test_file", job_name="test_job", url="http://example.com/testfile")


@pytest.fixture
def queued_downloader(job_dto, mock_journal_daemon):
    return QueuedDownloader(
        job=job_dto, monitor=mock_journal_daemon, worker_pool_size=1
    )


@pytest.mark.skip(reason="Mocking doesn't seem to work with multi-threading")
def test_download_file(queued_downloader, file_model_dto):
    with patch('aoget.web.downloader.download_file') as mock_download_file:
        queued_downloader.start_download_threads()
        queued_downloader.download_file(file_model_dto)
        time.sleep(0.1)
        queued_downloader.stop()

        mock_download_file.assert_called_once()
        assert mock_download_file.call_args[0][0] == file_model_dto.url
        assert mock_download_file.call_args[0][1].endswith(file_model_dto.name)


def test_stop_download_threads(queued_downloader):
    queued_downloader.start_download_threads()
    queued_downloader.stop()
    time.sleep(0.1)
    assert not queued_downloader.are_download_threads_running


def test_cancel_download(queued_downloader, file_model_dto):
    queued_downloader.download_file(file_model_dto)
    queued_downloader.cancel_download(file_model_dto.name)
    assert file_model_dto.name not in queued_downloader.files_in_queue
