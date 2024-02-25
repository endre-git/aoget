import pytest
from unittest.mock import MagicMock, patch
from aoget.controller.update_cycle import UpdateCycle
from aoget.model.job import Job
from aoget.model.dto.job_dto import JobDTO


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
            "test_job", update_cycle.job_updates, "Running"
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
            "test_job", update_cycle.job_updates, "Running"
        )
        # all updates ignored
        assert updated_job is None

    @patch("aoget.controller.update_cycle.get_job_dao")
    def test_update_job_in_db_no_update_equals_db_state(self, mock_get_job_dao, update_cycle):
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
            "test_job", update_cycle.job_updates, "Running"
        )

        assert updated_job.name == "test_job"
        assert updated_job.status == "Running"
        assert updated_job.page_url == "http://example.com"
