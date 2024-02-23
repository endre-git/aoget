import pytest
from unittest.mock import MagicMock, patch
from aoget.controller.update_cycle import UpdateCycle


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

