import pytest
import time
from unittest.mock import Mock
from aoget.web.journal_daemon import JournalDaemon


class TestJournalDaemon:
    @pytest.fixture
    def mock_journal_processor(self):
        return Mock()

    @pytest.fixture
    def daemon(self, mock_journal_processor):
        return JournalDaemon(journal_processor=mock_journal_processor)

    def test_update_download_progress(self, daemon):
        daemon.update_download_progress("job1", "file1", 500, 1000)
        assert "job1" in daemon._JournalDaemon__journal
        assert (
            daemon._JournalDaemon__journal["job1"]
            .file_model_updates["file1"]
            .downloaded_bytes
            == 500
        )

    def test_update_file_status(self, daemon):
        daemon.update_file_status("job1", "file1", "downloading", "no error")
        assert (
            daemon._JournalDaemon__journal["job1"].file_model_updates["file1"].status
            == "downloading"
        )

    def test_update_file_size(self, daemon):
        daemon.update_file_size("job1", "file1", 1000)
        assert (
            daemon._JournalDaemon__journal["job1"]
            .file_model_updates["file1"]
            .size_bytes
            == 1000
        )

    def test_journal_processing(self, daemon, mock_journal_processor):
        # Simulate update call
        daemon.update_download_progress("job1", "file1", 500, 1000)
        time.sleep(0.1)  # make sure we stop before the second tick which will be a blank update
        daemon.stop()
        # Verify that journal_processor's update_tick method was called with the correct data
        mock_journal_processor.update_tick.assert_called_once()
        args, _ = mock_journal_processor.update_tick.call_args
        assert "job1" in args[0]
        assert args[0]["job1"].file_model_updates["file1"].downloaded_bytes == 500

    def test_stop(self, daemon):
        daemon.stop()
        assert daemon._JournalDaemon__stopped
