import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from aoget.web.file_queue import FileQueue
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

        # mock_download_file.assert_called_once()
        # assert mock_download_file.call_args[0][0] == file_model_dto.url
        # assert mock_download_file.call_args[0][1].endswith(file_model_dto.name)


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


def test_shutdown(queued_downloader):
    queued_downloader.files_downloading.append("test_file")
    mock_signal = MagicMock()
    queued_downloader.signals = {"test_file": mock_signal}
    queued_downloader.shutdown()
    assert not queued_downloader.are_download_threads_running
    mock_signal.cancel.assert_called_once()


def test_dequeue_files(queued_downloader):
    file_model_dto_1 = FileModelDTO(
        name="testfile1",
        job_name="test_job",
        url="http://example.com/testfile1",
        priority=2,
    )
    file_model_dto_2 = FileModelDTO(
        name="testfile2",
        job_name="test_job",
        url="http://example.com/testfile2",
        priority=3,
    )
    file_model_dto_3 = FileModelDTO(
        name="testfile3",
        job_name="test_job",
        url="http://example.com/testfile3",
        priority=4,
    )
    queued_downloader.files_in_queue = ["testfile2", "testfile3"]
    queued_downloader.queue = MagicMock()
    queued_downloader.dequeue_files(
        [file_model_dto_1, file_model_dto_2, file_model_dto_3]
    )
    assert len(queued_downloader.files_in_queue) == 0
    queued_downloader.queue.remove_all.assert_called_with(
        [file_model_dto_1, file_model_dto_2, file_model_dto_3]
    )


def test_stop_active_downloads(queued_downloader):
    file_model_dto_1 = FileModelDTO(
        name="testfile1",
        job_name="test_job",
        url="http://example.com/testfile1",
        priority=2,
    )
    file_model_dto_2 = FileModelDTO(
        name="testfile2",
        job_name="test_job",
        url="http://example.com/testfile2",
        priority=3,
    )
    file_model_dto_3 = FileModelDTO(
        name="testfile3",
        job_name="test_job",
        url="http://example.com/testfile3",
        priority=4,
    )
    queued_downloader.files_downloading.append("testfile2")
    queued_downloader.files_downloading.append("testfile3")
    mock_signal_file2 = MagicMock()
    mock_signal_file3 = MagicMock()
    queued_downloader.signals = {
        "testfile2": mock_signal_file2,
        "testfile3": mock_signal_file3,
    }

    queued_downloader.stop_active_downloads(
        [file_model_dto_1, file_model_dto_2, file_model_dto_3]
    )
    assert (
        len(queued_downloader.files_downloading) == 2
    )  # they were not removed, just cancelled
    mock_signal_file2.cancel.assert_called_once()
    mock_signal_file3.cancel.assert_called_once()


def test_size_resolver(queued_downloader):
    file_model_dto_1 = FileModelDTO(
        name="testfile1",
        job_name="test_job",
        url="http://example.com/testfile1",
        priority=2,
    )
    file_model_dto_2 = FileModelDTO(
        name="testfile2",
        job_name="test_job",
        url="http://example.com/testfile2",
        priority=3,
    )
    file_model_dto_3 = FileModelDTO(
        name="testfile3",
        job_name="test_job",
        url="http://example.com/testfile3",
        priority=4,
    )
    with patch(
        "aoget.web.queued_downloader.resolve_remote_file_size"
    ) as mock_resolve_remote_file_size:
        mock_resolve_remote_file_size.return_value = 100
        thread = queued_downloader.resolve_file_sizes(
            "test_job", [file_model_dto_1, file_model_dto_2, file_model_dto_3]
        )
        thread.join()
        assert queued_downloader.journal_daemon.update_file_size.call_count == 3
        # first call was with "test_job", "testfile1", 100
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[0][0][0]
            == "test_job"
        )
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[0][0][1]
            == "testfile1"
        )
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[0][0][2]
            == 100
        )
        # second call was with "test_job", "testfile2", 100
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[1][0][0]
            == "test_job"
        )
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[1][0][1]
            == "testfile2"
        )
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[1][0][2]
            == 100
        )
        # third call was with "test_job", "testfile3", 100
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[2][0][0]
            == "test_job"
        )
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[2][0][1]
            == "testfile3"
        )
        assert (
            queued_downloader.journal_daemon.update_file_size.call_args_list[2][0][2]
            == 100
        )


def test_size_resolver_but_it_cant_resolve(queued_downloader):
    file_model_dto_1 = FileModelDTO(
        name="testfile1",
        job_name="test_job",
        url="http://example.com/testfile1",
        priority=2,
    )
    file_model_dto_2 = FileModelDTO(
        name="testfile2",
        job_name="test_job",
        url="http://example.com/testfile2",
        priority=3,
    )
    file_model_dto_3 = FileModelDTO(
        name="testfile3",
        job_name="test_job",
        url="http://example.com/testfile3",
        priority=4,
    )
    with patch(
        "aoget.web.queued_downloader.resolve_remote_file_size"
    ) as mock_resolve_remote_file_size:
        # raise an exception when resolve_remote_file_size is called
        mock_resolve_remote_file_size.side_effect = Exception
        thread = queued_downloader.resolve_file_sizes(
            "test_job", [file_model_dto_1, file_model_dto_2, file_model_dto_3]
        )
        thread.join()
        assert queued_downloader.journal_daemon.update_file_size.call_count == 0
        # journal daemon was called 10 attempts * 3 files = 30 times
        assert queued_downloader.journal_daemon.add_file_event.call_count == 30


def test_register_listener(queued_downloader):
    event = threading.Event()
    queued_downloader.signals["test_file"] = mocks_signal = MagicMock()
    queued_downloader.register_listener(event, "test_file", "Stopped")
    mocks_signal.register_status_listener.assert_called_once_with(event, "Stopped")


def test_is_checking_health(queued_downloader):
    assert not queued_downloader.is_checking_health()


def test_add_thread(queued_downloader):
    with patch('aoget.web.queued_downloader.threading.Thread') as mock_thread:
        queued_downloader.add_thread()
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
        assert len(queued_downloader.threads) == 1


def test_remove_thread_but_already_at_null(queued_downloader):
    assert len(queued_downloader.threads) == 0
    queued_downloader.remove_thread()
    assert len(queued_downloader.threads) == 0


def test_remove_thread(queued_downloader):
    with patch('aoget.web.queued_downloader.threading.Thread'):
        queued_downloader.add_thread()
        assert queued_downloader.worker_pool_size == 2
        queued_downloader.remove_thread()
        assert queued_downloader.worker_pool_size == 1
