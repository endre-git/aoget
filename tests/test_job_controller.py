import pytest
from unittest.mock import MagicMock, patch
from aoget.controller.job_controller import JobController
from aoget.model.job import Job


class TestJobController:
    """Test the JobController class."""

    @pytest.fixture
    def mock_app_state_handlers(self):
        return MagicMock()

    @pytest.fixture
    def mock_job_task_controller(self):
        return MagicMock()

    @pytest.fixture
    def mock_file_controller(self):
        return MagicMock()

    @pytest.fixture
    def mock_job_dao(self):
        return MagicMock()

    @pytest.fixture
    def job_controller(
        self, mock_app_state_handlers, mock_job_task_controller, mock_file_controller
    ):
        controller = JobController(
            app_state_handlers=mock_app_state_handlers,
            resume_callback=MagicMock(),
            message_callback=MagicMock(),
            background_controller=mock_job_task_controller,
        )
        controller.set_file_controller(mock_file_controller)
        return controller

    def test_initialization(self, job_controller):
        assert job_controller is not None

    def test_get_job_dtos(self, job_controller):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_dao:
            mock_dao.return_value.get_all_jobs.return_value = [MagicMock()]
            job_dtos = job_controller.get_job_dtos()
            assert len(job_dtos) == 1

    def test_get_job_dto_by_name(self, job_controller):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_dao:
            mock_dao.return_value.get_job_by_name.return_value = MagicMock()
            job_dto = job_controller.get_job_dto_by_name("test")
            assert job_dto is not None

    def test_job_post_select(self, job_controller, mock_job_dao):
        mock_job_dao.return_value.get_job_by_name.return_value = MagicMock()
        job_controller.job_post_select("test")
        job_controller.background_controller.resolve_file_sizes.assert_called_once_with(
            "test"
        )

    def test_resume_all_jobs(self, job_controller, mock_file_controller):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_dao:
            mock_dao.return_value.get_all_jobs.return_value = [
                Job(
                    id=-1,
                    name="Test Job",
                    status="Not Running",
                    page_url="http://example.com",
                ),
                Job(
                    id=-2,
                    name="Test Job 2",
                    status="Not Running",
                    page_url="http://example2.com",
                ),
            ]

            job_controller.resume_all_jobs()
            assert mock_file_controller.get_selected_file_dtos.call_count == 2

    def test_stop_all_jobs(self, job_controller, mock_file_controller):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_dao:
            mock_dao.return_value.get_all_jobs.return_value = [
                Job(
                    id=-1,
                    name="Test Job",
                    status="Running",
                    page_url="http://example.com",
                ),
                Job(
                    id=-2,
                    name="Test Job 2",
                    status="Running",
                    page_url="http://example2.com",
                ),
            ]

            job_controller.stop_all_jobs()
            assert mock_file_controller.get_selected_file_dtos.call_count == 2

    def test_add_job(self, job_controller):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_job_dao:
            job = Job(
                id=-1,
                name="Test Job",
                status="Not Running",
                page_url="http://example.com",
            )
            job_controller.add_job(job)
            mock_job_dao.return_value.add_job.assert_called_once_with(job)
            job_controller.background_controller.resolve_file_sizes.assert_called_once_with(
                "Test Job"
            )

    def test_start_job(self, job_controller, mock_file_controller):
        file_dto = MagicMock()
        mock_file_controller.get_selected_file_dtos.return_value = {
            "Test File": file_dto
        }
        job_controller.start_job("Test Job")
        mock_file_controller.get_selected_file_dtos.assert_called_once_with("Test Job")
        mock_file_controller.start_download_file_dto.assert_called_once_with(
            "Test Job", file_dto
        )

    def test_stop_job(
        self, job_controller, mock_app_state_handlers, mock_file_controller
    ):
        file_dto = MagicMock()
        mock_file_controller.get_selected_file_dtos.return_value = {
            "Test File": file_dto
        }
        mock_app_state_handlers.downloads.is_running_for_job.return_value = True
        job_controller.stop_job("Test Job")
        mock_app_state_handlers.downloads.is_running_for_job.assert_called_once_with(
            "Test Job"
        )
        mock_file_controller.get_selected_file_dtos.assert_called_once_with("Test Job")
        mock_file_controller.stop_download_file_dto.assert_called_once_with(
            "Test Job", file_dto
        )

    def test_add_thread(self, job_controller, mock_app_state_handlers):
        downloader_mock = mock_app_state_handlers.downloads.get_downloader.return_value
        downloader_mock.worker_pool_size = 1
        downloader_mock.get_active_thread_count.return_value = 1
        job_controller.add_thread("Test Job")
        downloader_mock.add_thread.assert_called_once()
        journal_mock = mock_app_state_handlers.update_cycle.journal_of_job.return_value
        journal_mock.update_job_threads.assert_called_once_with(
            threads_allocated=1, threads_active=1
        )

    def test_remove_thread_already_at_minimum(self, job_controller, mock_app_state_handlers):
        downloader_mock = mock_app_state_handlers.downloads.get_downloader.return_value
        downloader_mock.worker_pool_size = 1
        job_controller.remove_thread("Test Job")
        assert downloader_mock.remove_thread.call_count == 0
        assert mock_app_state_handlers.update_cycle.journal_of_job.call_count == 0

    def test_remove_thread_no_need_to_kill_download(self, job_controller, mock_app_state_handlers):
        downloader_mock = mock_app_state_handlers.downloads.get_downloader.return_value
        downloader_mock.worker_pool_size = 2
        downloader_mock.get_active_thread_count.return_value = 1
        job_controller.remove_thread("Test Job")
        assert downloader_mock.remove_thread.call_count == 1
