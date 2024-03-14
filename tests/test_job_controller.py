import os
import pytest
from unittest.mock import MagicMock, patch
from aoget.controller.job_controller import JobController
from aoget.model.job import Job
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.model.dto.job_dto import JobDTO


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
        with patch("aoget.controller.job_controller.get_job_dao"):
            mock_file_controller.get_selected_file_dtos.return_value = {
                "Test File": file_dto
            }
            job_controller.start_job("Test Job")
            mock_file_controller.get_selected_file_dtos.assert_called_once_with("Test Job")
            mock_file_controller.start_download_file_dtos.assert_called_once()

    def test_stop_job(
        self, job_controller, mock_app_state_handlers, mock_file_controller
    ):
        with patch("aoget.controller.job_controller.get_job_dao"):
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
            mock_file_controller.stop_download_file_dtos.assert_called_once()

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

    def test_remove_thread_already_at_minimum(
        self, job_controller, mock_app_state_handlers
    ):
        downloader_mock = mock_app_state_handlers.downloads.get_downloader.return_value
        downloader_mock.worker_pool_size = 1
        job_controller.remove_thread("Test Job")
        assert downloader_mock.remove_thread.call_count == 0
        assert mock_app_state_handlers.update_cycle.journal_of_job.call_count == 0

    def test_remove_thread_no_need_to_kill_download(
        self, job_controller, mock_app_state_handlers
    ):
        downloader_mock = mock_app_state_handlers.downloads.get_downloader.return_value
        downloader_mock.worker_pool_size = 2
        downloader_mock.get_active_thread_count.return_value = 1
        job_controller.remove_thread("Test Job")
        assert downloader_mock.remove_thread.call_count == 1

    def test_remove_thread_lowest_priority_gets_stopped(
        self, job_controller, mock_app_state_handlers, mock_file_controller
    ):
        downloader_mock = mock_app_state_handlers.downloads.get_downloader.return_value
        downloader_mock.worker_pool_size = 2
        downloader_mock.get_active_thread_count.return_value = 2
        downloader_mock.files_downloading = ["Test File HI", "Test File LO"]
        higher_priority_file = FileModelDTO(
            job_name="Test Job", name="Test File HI", priority=1, status="Downloading"
        )
        lower_priority_file = FileModelDTO(
            job_name="Test Job", name="Test File LO", priority=2, status="Downloading"
        )
        selected_file_dtos = {
            "Test File HI": higher_priority_file,
            "Test File LO": lower_priority_file,
        }
        mock_file_controller.get_selected_file_dtos.return_value = selected_file_dtos
        job_controller.remove_thread("Test Job")
        assert downloader_mock.remove_thread.call_count == 1
        mock_file_controller.stop_download.assert_called_once()
        assert mock_file_controller.stop_download.call_args.args == (
            "Test Job",
            "Test File LO",
        )

    def test_delete_job(self, job_controller, mock_app_state_handlers):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_dao:
            journal = MagicMock()
            mock_app_state_handlers.journal_daemon = journal
            job_controller.delete_job("Test Job")
            downloads = mock_app_state_handlers.downloads
            update_cycle = mock_app_state_handlers.update_cycle
            cache = mock_app_state_handlers.cache
            downloads.shutdown_for_job.assert_called_once_with("Test Job")
            update_cycle.drop_job.assert_called_once_with("Test Job")
            cache.drop_job.assert_called_once_with("Test Job")
            mock_dao.return_value.delete_job_by_name.assert_called_once_with("Test Job")
            journal.drop_job.assert_called_once_with("Test Job")

    def test_delete_job_with_files(
        self, job_controller, mock_app_state_handlers, mock_file_controller
    ):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_dao, patch(
            "aoget.controller.job_controller.os.path.exists"
        ) as mock_path_exists, patch(
            "aoget.controller.job_controller.os.remove"
        ) as mock_os_remove:
            higher_priority_file = FileModelDTO(
                job_name="Test Job",
                name="Test File HI",
                priority=1,
                status="Downloading",
            )
            lower_priority_file = FileModelDTO(
                job_name="Test Job",
                name="Test File LO",
                priority=2,
                status="Downloading",
            )
            selected_file_dtos = {
                "Test File HI": higher_priority_file,
                "Test File LO": lower_priority_file,
            }
            mock_file_controller.get_selected_file_dtos.return_value = (
                selected_file_dtos
            )
            mock_dao.return_value.get_job_by_name.return_value = Job(
                id=-1,
                name="Test Job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )
            downloads = mock_app_state_handlers.downloads
            update_cycle = mock_app_state_handlers.update_cycle
            cache = mock_app_state_handlers.cache
            mock_path_exists.return_value = True
            job_controller.delete_job("Test Job", delete_from_disk=True)

            assert mock_os_remove.call_count == 2
            assert mock_os_remove.call_args_list[0].args == (os.path.join(
                "fake_path", "Test File HI"
            ),)
            assert mock_os_remove.call_args_list[1].args == (os.path.join(
                "fake_path", "Test File LO"
            ),)

            # mock_os_remove.assert_called_once_with("fake_path")
            downloads.shutdown_for_job.assert_called_once_with("Test Job")
            update_cycle.drop_job.assert_called_once_with("Test Job")
            cache.drop_job.assert_called_once_with("Test Job")
            mock_dao.return_value.delete_job_by_name.assert_called_once_with("Test Job")

    def test_update_job_from_dto(self, job_controller):
        with patch("aoget.controller.job_controller.get_job_dao") as mock_dao:
            job_dto = JobDTO(
                id=-1,
                name="Test Job",
                status="Not Running",
                page_url="http://example.com",
            )
            job_controller.update_job_from_dto(job_dto)
            mock_dao.return_value.save_job.assert_called_once()
