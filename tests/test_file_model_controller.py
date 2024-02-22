import pytest
from unittest.mock import MagicMock, patch
from aoget.controller.file_model_controller import FileModelController
from aoget.model.job import Job
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.model.file_model import FileModel
from aoget.model.dto.job_dto import JobDTO
from aoget.controller.app_cache import AppCache
from aoget.controller.app_state_handlers import AppStateHandlers
from aoget.controller.downloads import Downloads


class TestFileModelController:

    @pytest.fixture
    def mock_app_state_handlers(self, app_cache):
        mock_handlers = AppStateHandlers(
            MagicMock(), MagicMock(), start_journal_daemon=False
        )
        mock_handlers.cache = app_cache
        return mock_handlers

    @pytest.fixture
    def mock_job_controller(self):
        return MagicMock()

    @pytest.fixture
    def mock_job_dao(self):
        return MagicMock()

    @pytest.fixture
    def file_model_controller(self, mock_app_state_handlers):
        controller = FileModelController(
            app_state_handlers=mock_app_state_handlers,
        )
        return controller

    @pytest.fixture
    def app_cache(self):
        app_cache = AppCache()
        app_cache.set_cache(
            {
                'test_job': {
                    'file_name': FileModelDTO(
                        job_name='test_job', name='file_name', status='Downloading'
                    ),
                    'file_name2': FileModelDTO(
                        job_name='test_job', name='file_name2', status='Downloading'
                    ),
                    'file_name3': FileModelDTO(
                        job_name='test_job', name='file_name3', status='Downloading'
                    ),
                }
            }
        )

    @pytest.fixture
    def mock_file_set(self):
        test_job = Job(
            id=-1,
            name="test_job",
            status="Not Running",
            page_url="http://example.com",
            target_folder="fake_path",
        )
        return [
            FileModel(test_job, 'http://example.com/testfile1'),
            FileModel(test_job, 'http://example.com/testfile2'),
            FileModel(test_job, 'http://example.com/testfile3'),
            FileModel(test_job, 'http://example.com/testfile4'),
            FileModel(test_job, 'http://example.com/testfile5'),
        ]

    def test_initialization(self, file_model_controller):
        assert file_model_controller is not None

    def test_get_selected_file_dtos_cached(self, file_model_controller):
        cache = AppCache()
        cache.set_cache(
            {
                'test_job': {
                    'file_name': FileModelDTO(
                        job_name='test_job', name='file_name', status='Downloading'
                    ),
                    'file_name2': FileModelDTO(
                        job_name='test_job', name='file_name2', status='Downloading'
                    ),
                    'file_name3': FileModelDTO(
                        job_name='test_job', name='file_name3', status='Downloading'
                    ),
                }
            }
        )
        file_model_controller.app.cache = cache
        file_dtos = file_model_controller.get_selected_file_dtos('test_job')
        assert len(file_dtos) == 3
        assert file_dtos['file_name'].status == 'Downloading'
        assert file_dtos['file_name2'].status == 'Downloading'
        assert file_dtos['file_name3'].status == 'Downloading'

    def test_get_selected_file_dtos_not_cached(
        self, file_model_controller, mock_file_set
    ):
        cache = AppCache()
        file_model_controller.app.cache = cache
        with patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ) as mock_job_dao, patch(
            'aoget.controller.file_model_controller.get_file_model_dao'
        ) as mock_file_model_dao:
            mock_job_dao.return_value.get_job_by_name.return_value = JobDTO(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )
            mock_file_model_dao.return_value.get_selected_files_of_job.return_value = (
                mock_file_set
            )
            file_dtos = file_model_controller.get_selected_file_dtos('test_job')
            assert len(file_dtos) == 5

    def test_remove_file_from_job_not_running(self, file_model_controller):
        cache = AppCache()
        cache.set_cache(
            {
                'test_job': {
                    'file_name': FileModelDTO(
                        job_name='test_job', name='file_name', status='Stopped'
                    ),
                    'file_name2': FileModelDTO(
                        job_name='test_job', name='file_name2', status='Stopped'
                    ),
                    'file_name3': FileModelDTO(
                        job_name='test_job', name='file_name3', status='Stopped'
                    ),
                }
            }
        )
        file_model_controller.app.cache = cache
        file_model_controller.remove_file_from_job('test_job', 'file_name')
        # deselection shows up in journal
        journal = file_model_controller.app.update_cycle.journal_of_job('test_job')
        assert "file_name" in journal.file_model_updates
        assert journal.file_model_updates["file_name"].selected is False

    def test_remove_file_from_job_queued(self, file_model_controller):
        file_model_controller.app.downloads = MagicMock()
        file_model_controller.app.downloads.is_file_queued.return_value = True

        file_model_controller.remove_file_from_job('test_job', 'file_name')
        get_downloader_method = file_model_controller.app.downloads.get_downloader
        get_downloader_method.assert_called_once_with('test_job')
        get_downloader_method.return_value.cancel_download.assert_called_once_with(
            'file_name'
        )
        # deselection shows up in journal
        journal = file_model_controller.app.update_cycle.journal_of_job('test_job')
        assert "file_name" in journal.file_model_updates
        assert journal.file_model_updates["file_name"].selected is False

    def test_stop_download_download_did_not_start_yet(self, file_model_controller):
        dl = MagicMock()
        file_model_controller.app.downloads = dl
        dl.is_running_for_job.return_value = True
        job_downloader_mock = dl.get_downloader.return_value

        (result, status) = file_model_controller.stop_download('test_job', 'file_name')
        job_downloader_mock.cancel_download.assert_called_once_with('file_name')
        assert status == 'Stopped'

    def test_stop_download_download_running(self, file_model_controller):
        dl = MagicMock()
        file_model_controller.app.downloads = dl
        dl.is_running_for_job.return_value = True
        job_downloader_mock = dl.get_downloader.return_value
        cancel_mock = MagicMock()
        job_downloader_mock.signals = {'file_name': cancel_mock}

        (result, status) = file_model_controller.stop_download('test_job', 'file_name')
        cancel_mock.cancel.assert_called_once()
        assert status == 'Stopping'
