import pytest
from unittest.mock import MagicMock, patch
from aoget.controller.update_cycle import UpdateCycle
from aoget.model.job_updates import JobUpdates
from aoget.model.job import Job
from aoget.model.dto.job_dto import JobDTO
from aoget.model.file_model import FileModel
from aoget.model.dto.file_model_dto import FileModelDTO


class TestUpdateCycle:

    @pytest.fixture
    def update_cycle(self, app_state_handlers, main_window):
        return UpdateCycle(app_state_handlers, main_window)

    @pytest.fixture
    def app_state_handlers(self):
        return MagicMock()

    @pytest.fixture
    def main_window(self):
        return MagicMock()

    def test_initialization(self, update_cycle, app_state_handlers, main_window):
        assert update_cycle.journal == {}
        assert update_cycle.app == app_state_handlers
        assert update_cycle.main_window == main_window

    def test_journal_of_job(self, update_cycle):
        job_name = "test_job"
        journal = update_cycle.journal_of_job(job_name)
        assert journal.job_name == job_name

    def test_create_journal(self, update_cycle):
        job_name = "test_job"
        update_cycle.create_journal(job_name)
        assert job_name in update_cycle.journal

    def test_drop_job(self, update_cycle):
        job_name = "test_job"
        update_cycle.journal[job_name] = MagicMock()
        update_cycle.drop_job(job_name)
        assert job_name not in update_cycle.journal

    @patch("aoget.controller.update_cycle.get_job_dao")
    def test_process_job_updates_merge(self, update_cycle):
        cycle_job_updates = MagicMock()
        cycle_job_updates.job_name = "test_job"
        update_cycle.journal = {"test_job": MagicMock()}

        update_cycle.process_job_updates(cycle_job_updates, merge=True)

        assert update_cycle.journal["test_job"].merge.called_once_with(
            cycle_job_updates
        )

    @patch("aoget.controller.update_cycle.get_job_dao")
    def test_update_job_in_db(self, mock_get_job_dao, update_cycle):
        # create mock DB as retrieved from DB
        test_job = Job(
            id=100,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        mock_get_job_dao.return_value.get_job_by_name.return_value = test_job

        # create job update which updates some fields
        mock_job_update = JobDTO(id=-1, name="test_job", total_size_bytes=10000)

        update_cycle.job_updates = MagicMock()
        update_cycle.job_updates.job_update = mock_job_update
        # assume that the returned result reflects updates
        updated_job = update_cycle._UpdateCycle__update_job_in_db(
            "test_job", update_cycle.job_updates
        )
        assert updated_job.total_size_bytes == 10000

    @patch("aoget.controller.update_cycle.get_job_dao")
    def test_update_job_in_db_stale_update(self, mock_get_job_dao, update_cycle):
        # create mock DB as retrieved from DB
        mock_get_job_dao.return_value.get_job_by_name.return_value = None

        # create job update which updates some fields
        mock_job_update = JobDTO(id=-1, name="test_job", total_size_bytes=10000)

        update_cycle.job_updates = MagicMock()
        update_cycle.job_updates.job_update = mock_job_update
        # assume that the returned result reflects updates
        updated_job = update_cycle._UpdateCycle__update_job_in_db(
            "test_job", update_cycle.job_updates
        )
        # all updates ignored
        assert updated_job is None

    @patch("aoget.controller.update_cycle.get_job_dao")
    def test_update_job_in_db_no_update_equals_db_state(
        self, mock_get_job_dao, update_cycle
    ):
        # create mock DB as retrieved from DB
        test_job = Job(
            id=100,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        mock_get_job_dao.return_value.get_job_by_name.return_value = test_job

        # create job update which updates some fields

        update_cycle.job_updates = MagicMock()
        update_cycle.job_updates.job_update = None
        # assume that the returned result reflects updates
        updated_job = update_cycle._UpdateCycle__update_job_in_db(
            "test_job", update_cycle.job_updates
        )

        assert updated_job.name == "test_job"
        assert updated_job.status == "Not Running"
        assert updated_job.page_url == "http://example.com"

    @patch("aoget.controller.update_cycle.get_job_dao")
    def test_process_updates_but_job_is_stale(self, mock_get_job_dao, update_cycle):
        mock_get_job_dao.return_value.get_job_by_name.return_value = None
        update_cycle.journal = {"test_job": MagicMock()}
        update_cycle.job_updates = MagicMock()
        update_cycle.job_updates.job_update = None

        update_cycle.process_job_updates(MagicMock(), merge=False)
        mock_get_job_dao.return_value.save_job.assert_not_called()

    @patch("aoget.controller.update_cycle.get_job_dao")
    @patch("aoget.controller.update_cycle.get_file_model_dao")
    @patch("aoget.controller.update_cycle.get_file_event_dao")
    def test_update_tick(
        self,
        mock_get_file_event_dao,
        mock_get_file_model_dao,
        mock_get_job_dao,
        update_cycle,
    ):

        job1 = Job(
            id=100,
            name="test_job1",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        job2 = Job(
            id=101,
            name="test_job2",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        file1 = FileModel(job2, 'http://example.com/file1')
        file2 = FileModel(job2, 'http://example.com/file2')

        mock_get_job_dao.return_value.get_job_by_name.side_effect = (
            lambda *args, **kwargs: (job1 if args[0] == "test_job1" else job2)
        )
        mock_get_file_model_dao.return_value.get_file_model_by_name.side_effect = (
            lambda *args, **kwargs: (file1 if args[1] == "file1" else file2)
        )

        # the journal in update cycle
        own_journal = {"test_job1": JobUpdates("test_job1")}
        own_journal["test_job1"].update_file_status("file1", "Stopped")
        # the journal coming with the update tick (emitted by journal daemon normally)
        tick_journal = {
            "test_job1": JobUpdates("test_job1"),
            "test_job2": JobUpdates("test_job2"),
        }
        tick_journal["test_job1"].update_job_threads(10, 0)
        tick_journal["test_job2"].update_file_status("file1", "Downloading")
        tick_journal["test_job2"].update_file_status("file2", "Downloading")
        tick_journal["test_job2"].update_file_download_progress("file1", 1000, 10000)
        tick_journal["test_job2"].update_file_download_progress("file2", 2000, 10000)
        update_cycle.journal = own_journal
        file_model_dto = FileModelDTO.from_model(
            file1, "test_job1"
        )
        file_model_dto.selected = True
        update_cycle.app.cache.get_cached_file.return_value = file_model_dto
        update_cycle.update_tick(tick_journal)
        assert file1.downloaded_bytes == 1000
        assert file2.downloaded_bytes == 2000
        assert file2.status == "Downloading"
        assert job1.threads_allocated == 10

    @patch("aoget.controller.update_cycle.get_job_dao")
    @patch("aoget.controller.update_cycle.get_file_model_dao")
    @patch("aoget.controller.update_cycle.get_file_event_dao")
    def test_update_tick_file_deselected(
        self,
        mock_get_file_event_dao,
        mock_get_file_model_dao,
        mock_get_job_dao,
        update_cycle,
    ):

        job1 = Job(
            id=100,
            name="test_job1",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        job2 = Job(
            id=101,
            name="test_job2",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
            selected_files_count=2,
            selected_files_with_known_size=2,
            total_size_bytes=50000,
            downloaded_bytes=10000,
        )
        file1 = FileModel(job2, 'http://example.com/file1')
        file2 = FileModel(job2, 'http://example.com/file2')

        mock_get_job_dao.return_value.get_job_by_name.side_effect = (
            lambda *args, **kwargs: (job1 if args[0] == "test_job1" else job2)
        )
        mock_get_file_model_dao.return_value.get_file_model_by_name.side_effect = (
            lambda *args, **kwargs: (file1 if args[1] == "file1" else file2)
        )

        # the journal in update cycle
        own_journal = {"test_job1": JobUpdates("test_job1")}
        own_journal["test_job1"].update_file_status("file1", "Stopped")
        # the journal coming with the update tick (emitted by journal daemon normally)
        tick_journal = {
            "test_job1": JobUpdates("test_job1"),
            "test_job2": JobUpdates("test_job2"),
        }
        tick_journal["test_job1"].update_job_threads(10, 0)
        tick_journal["test_job2"].update_file_status("file1", "Downloading")
        tick_journal["test_job2"].update_file_status("file2", "Downloading")
        tick_journal["test_job2"].update_file_download_progress("file1", 1000, 10000)
        tick_journal["test_job2"].update_file_download_progress("file2", 2000, 10000)
        update_cycle.journal = own_journal
        file_model_dto = FileModelDTO.from_model(
            file1, "test_job2"
        )
        file_model_dto.selected = False
        update_cycle.app.cache.get_cached_file.return_value = file_model_dto
        update_cycle.update_tick(tick_journal)
        assert file1.downloaded_bytes == 1000
        assert file2.downloaded_bytes == 2000
        assert file2.status == "Downloading"
        assert job2.selected_files_count == 1

    @patch("aoget.controller.update_cycle.get_job_dao")
    @patch("aoget.controller.update_cycle.get_file_model_dao")
    @patch("aoget.controller.update_cycle.get_file_event_dao")
    def test_fix_183(
        self,
        mock_get_file_event_dao,
        mock_get_file_model_dao,
        mock_get_job_dao,
        update_cycle,
    ):
        """https://github.com/endre-git/aoget/issues/183"""

        job1 = Job(
            id=100,
            name="test_job1",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        job2 = Job(
            id=101,
            name="test_job2",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        file1 = FileModel(job2, 'http://example.com/file1')
        file2 = FileModel(job2, 'http://example.com/file2')

        mock_get_job_dao.return_value.get_job_by_name.side_effect = (
            lambda *args, **kwargs: (job1 if args[0] == "test_job1" else job2)
        )
        mock_get_file_model_dao.return_value.get_file_model_by_name.side_effect = (
            lambda *args, **kwargs: (file1 if args[1] == "file1" else file2)
        )

        # the journal in update cycle
        own_journal = {"test_job1": JobUpdates("test_job1")}
        own_journal["test_job1"].update_file_status("file1", "Stopped")
        # the journal coming with the update tick (emitted by journal daemon normally)
        tick_journal = {
            "test_job1": JobUpdates("test_job1"),
            "test_job2": JobUpdates("test_job2"),
        }
        tick_journal["test_job1"].update_job_threads(10, 0)
        tick_journal["test_job2"].update_file_status("file1", "Downloading")
        tick_journal["test_job2"].update_file_status("file2", "Downloading")
        tick_journal["test_job2"].update_file_download_progress("file1", 1000, 10000)
        tick_journal["test_job2"].update_file_download_progress("file2", 2000, 10000)
        update_cycle.journal = own_journal
        file_model_dto = FileModelDTO.from_model(
            file1, "test_job1"
        )
        file_model_dto.selected = True
        update_cycle.app.cache.get_cached_file.return_value = file_model_dto
        update_cycle.update_tick(tick_journal)
        assert file1.downloaded_bytes == 1000
        assert file2.downloaded_bytes == 2000
        assert file2.status == "Downloading"
        assert job1.threads_allocated == 10
