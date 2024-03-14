import os
import pytest
from unittest.mock import MagicMock, patch
from aoget.controller.file_model_controller import FileModelController
from aoget.model.job import Job
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.model.file_model import FileModel
from aoget.model.dto.job_dto import JobDTO
from aoget.controller.app_cache import AppCache
from aoget.controller.app_state_handlers import AppStateHandlers
from aoget.model.file_event import FileEvent


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

    def test_get_file_event_dtos(self, file_model_controller):
        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ), patch(
            'aoget.controller.file_model_controller.get_file_event_dao'
        ) as mock_file_event_dao:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )
            file_model = FileModel(test_job, 'http://example.com/testfile1')
            mock_file_event_dao.return_value.get_file_events_by_file_id.return_value = [
                FileEvent(event="Event 1", file=file_model),
                FileEvent(event="Event 2", file=file_model),
                FileEvent(event="Event 3", file=file_model),
            ]

            dtos = file_model_controller.get_file_event_dtos("test_job", "file_name")
            assert len(dtos) == 3

    def test_resolve_local_file_path(self, file_model_controller):
        with patch(
            'aoget.controller.file_model_controller.get_file_model_dao'
        ) as file_dao_mock, patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ) as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )
            file_model = FileModel(test_job, 'http://example.com/testfile1')
            job_dao_mock.return_value.get_job_by_name.return_value = test_job
            file_dao_mock.return_value.get_file_model_by_name.return_value = file_model
            resolved_path = file_model_controller.resolve_local_file_path(
                'test_job', 'file_name'
            )
            assert resolved_path == os.path.join('fake_path', 'testfile1')

    def test_set_files_of_job(self, file_model_controller):
        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ) as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )

            file_dto_1 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name',
                name='file_name',
                status='Stopped',
                selected=True,
                size_bytes=100,
            )
            file_dto_2 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name2',
                name='file_name2',
                status='Stopped',
                selected=True,
                size_bytes=100,
            )
            file_dto_3 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name3',
                name='file_name3',
                status='Stopped',
                selected=True,
                size_bytes=100,
            )
            cache = AppCache()
            file_model_controller.app.cache = cache
            job_dao_mock.return_value.get_job_by_id.return_value = test_job
            file_model_controller.set_files_of_job(
                'test_job', [file_dto_1, file_dto_2, file_dto_3]
            )
            assert test_job.selected_files_count == 3
            assert len(cache.get_cache()['test_job']) == 3

    def test_increase_file_priorities(self, file_model_controller):
        cache = AppCache()
        cache.set_cache(
            {
                'test_job': {
                    'file_name': FileModelDTO(
                        job_name='test_job',
                        name='file_name',
                        status='Downloading',
                        priority=2,
                    ),
                    'file_name2': FileModelDTO(
                        job_name='test_job',
                        name='file_name2',
                        status='Downloading',
                        priority=3,
                    ),
                    'file_name3': FileModelDTO(
                        job_name='test_job',
                        name='file_name3',
                        status='Downloading',
                        priority=1,
                    ),
                }
            }
        )
        file_model_controller.app.cache = cache
        file_model_controller.increase_file_priorities(
            'test_job', ['file_name', 'file_name2', 'file_name3']
        )
        assert cache.get_cache()['test_job']['file_name'].priority == 1
        assert cache.get_cache()['test_job']['file_name2'].priority == 2
        assert cache.get_cache()['test_job']['file_name3'].priority == 1

    def test_decrease_file_priorities(self, file_model_controller):
        cache = AppCache()
        cache.set_cache(
            {
                'test_job': {
                    'file_name': FileModelDTO(
                        job_name='test_job',
                        name='file_name',
                        status='Downloading',
                        priority=2,
                    ),
                    'file_name2': FileModelDTO(
                        job_name='test_job',
                        name='file_name2',
                        status='Downloading',
                        priority=3,
                    ),
                    'file_name3': FileModelDTO(
                        job_name='test_job',
                        name='file_name3',
                        status='Downloading',
                        priority=1,
                    ),
                }
            }
        )
        file_model_controller.app.cache = cache
        file_model_controller.decrease_file_priorities(
            'test_job', ['file_name', 'file_name2', 'file_name3']
        )
        assert cache.get_cache()['test_job']['file_name'].priority == 3
        assert cache.get_cache()['test_job']['file_name2'].priority == 3
        assert cache.get_cache()['test_job']['file_name3'].priority == 2

    def test_update_selected_files_of_job(self, file_model_controller):
        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ) as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )

            file_dto_1 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name',
                name='file_name',
                status='Stopped',
                selected=False,
                size_bytes=100,
            )
            file_dto_2 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name2',
                name='file_name2',
                status='Stopped',
                selected=False,
                size_bytes=100,
            )
            file_dto_3 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name3',
                name='file_name3',
                status='Stopped',
                selected=True,
                size_bytes=100,
            )
            file_1 = FileModel(test_job, 'http://example.com/file_name')
            file_2 = FileModel(test_job, 'http://example.com/file_name2')
            file_3 = FileModel(test_job, 'http://example.com/file_name3')
            test_job.files = [file_1, file_2, file_3]
            cache = AppCache()
            file_model_controller.app.cache = cache
            job_dao_mock.return_value.get_job_by_id.return_value = test_job
            file_dtos_by_name = {
                'file_name': file_dto_1,
                'file_name2': file_dto_2,
                'file_name3': file_dto_3,
            }
            file_model_controller.update_selected_files_of_job(-1, file_dtos_by_name)
            assert test_job.selected_files_count == 1
            assert len(cache.get_cache()['test_job']) == 1

    def test_start_download_file_dto(self, file_model_controller):
        file_dto_1 = FileModelDTO(
            job_name='test_job',
            url='http://example.com/file_name',
            name='file_name',
            status='Stopped',
            selected=False,
            size_bytes=100,
        )
        cache = AppCache()
        file_model_controller.app.cache = cache
        file_model_controller.app.downloads = MagicMock()
        journal = file_model_controller.app.update_cycle.journal_of_job('test_job')
        file_model_controller.start_download_file_dto('test_job', file_dto_1)
        assert journal.file_model_updates['file_name'].status == 'In queue'

    def test_stop_download_file_dto(self, file_model_controller):
        file_dto_1 = FileModelDTO(
            job_name='test_job',
            url='http://example.com/file_name',
            name='file_name',
            status='In queue',
            selected=False,
            size_bytes=100,
        )
        cache = AppCache()
        file_model_controller.app.cache = cache
        downloads = MagicMock()
        file_model_controller.app.downloads = MagicMock()
        downloads.is_running_for_job.return_value = True
        journal = file_model_controller.app.update_cycle.journal_of_job('test_job')
        file_model_controller.stop_download_file_dto('test_job', file_dto_1)
        assert journal.file_model_updates['file_name'].status == 'Stopped'

    def test_start_download(self, file_model_controller):
        downloads = MagicMock()
        file_model_controller.app.downloads = downloads
        downloads.is_file_queued.return_value = True
        (result, _) = file_model_controller.start_download('test_job', 'file_name')
        assert result is False
        downloads.is_file_queued.return_value = False
        downloads.is_file_downloading.return_value = True
        (result, _) = file_model_controller.start_download('test_job', 'file_name')
        assert result is False

    def test_start_download_actually_starts(self, file_model_controller):
        file_dto_1 = FileModelDTO(
            job_name='test_job',
            url='http://example.com/file_name',
            name='file_name',
            status='Stopped',
            selected=False,
            size_bytes=100,
        )
        cache = AppCache()
        cache.set_cache(
            {
                'test_job': {
                    'file_name': file_dto_1,
                }
            }
        )
        file_model_controller.app.cache = cache
        downloads = MagicMock()
        file_model_controller.app.downloads = downloads
        job_downloader_mock = MagicMock()
        downloads.is_file_queued.return_value = False
        downloads.is_file_downloading.return_value = False
        downloads.get_downloader.return_value = job_downloader_mock
        with patch(
            'aoget.controller.file_model_controller.get_file_model_dao'
        ) as file_dao_mock, patch('aoget.controller.file_model_controller.get_job_dao'):
            file_model = FileModel(
                Job(
                    id=-1,
                    name="test_job",
                    status="Not Running",
                    page_url="http://example.com",
                    target_folder="fake_path",
                ),
                'http://example.com/file_name',
            )
            file_dao_mock.return_value.get_file_model_by_name.return_value = file_model
            (result, _) = file_model_controller.start_download('test_job', 'file_name')
            job_downloader_mock.download_file.assert_called_once()
            assert result is True

    def test_redownload_file(self, file_model_controller):
        downloads = MagicMock()
        file_model_controller.app.downloads = downloads
        downloads.is_running_for_job.return_value = True
        downloads.is_file_downloading.return_value = True
        downloads.is_file_queued.return_value = False
        with patch('aoget.controller.file_model_controller.Event'), patch(
            'aoget.controller.file_model_controller.get_file_model_dao'
        ) as file_dao_mock, patch('aoget.controller.file_model_controller.get_job_dao'):
            file_model = FileModel(
                Job(
                    id=-1,
                    name="test_job",
                    status="Not Running",
                    page_url="http://example.com",
                    target_folder="fake_path",
                ),
                'http://example.com/file_name',
            )
            file_dao_mock.return_value.get_file_model_by_name.return_value = file_model
            file_model_controller.redownload_file('test_job', 'file_name')

    def test_start_downloads(self, file_model_controller):
        downloads = MagicMock()
        file_model_controller.app.downloads = downloads
        mock_downloader = MagicMock()
        downloads.get_downloader.return_value = mock_downloader
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

        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ):
            file_model_controller.start_downloads(
                'test_job', ['file_name', 'file_name2']
            )

    def test_stop_downloads(self, file_model_controller):
        downloads = MagicMock()
        file_model_controller.app.downloads = downloads
        mock_downloader = MagicMock()
        downloads.get_downloader.return_value = mock_downloader
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

        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ):
            file_model_controller.stop_downloads(
                'test_job', ['file_name', 'file_name2']
            )

    def test_remove_files_from_job(self, file_model_controller):
        downloads = MagicMock()
        file_model_controller.app.downloads = downloads
        mock_downloader = MagicMock()
        downloads.get_downloader.return_value = mock_downloader
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

        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ):
            file_model_controller.remove_files_from_job(
                'test_job', ['file_name', 'file_name2']
            )

    def test_get_all_files_in_job_folders(self, file_model_controller):
        with patch(
            'aoget.controller.file_model_controller.get_all_file_names_from_folders',
            return_value=['testfile1', 'testfile2', 'testfile3'],
        ), patch('aoget.controller.file_model_controller.get_job_dao') as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )
            job_dao_mock.return_value.get_all_jobs.return_value = [test_job]
            files = file_model_controller.all_files_in_job_folders()
            assert len(files) == 3

    def test_get_all_files_in_jobs(self, file_model_controller):
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
        with patch(
            'aoget.controller.file_model_controller.get_all_file_names_from_folders',
            return_value=['testfile1', 'testfile2', 'testfile3'],
        ), patch('aoget.controller.file_model_controller.get_job_dao') as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )
            job_dao_mock.return_value.get_all_jobs.return_value = [test_job]
            files = file_model_controller.all_files_in_jobs()
            assert len(files) == 3

    def test_get_file_dtos_by_job_id(self, file_model_controller):
        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ) as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )

            file_model_controller.app.cache = AppCache()
            job_dao_mock.return_value.get_job_by_id.return_value = test_job
            file_model_controller.get_file_dtos_by_job_id(-1)
            assert not file_model_controller.app.cache.is_cached_job('test_job')

    def test_start_download_file_dtos(self, file_model_controller):
        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ) as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )

            file_dto_1 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name',
                name='file_name',
                status='Downloading',
                selected=False,
                size_bytes=100,
            )
            file_dto_2 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name2',
                name='file_name2',
                status='Stopped',
                selected=False,
                size_bytes=100,
            )
            file_dto_3 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name3',
                name='file_name3',
                status='Stopped',
                selected=True,
                size_bytes=100,
            )
            cache = AppCache()
            dl = MagicMock()
            file_model_controller.app.downloads = dl
            dl.is_running_for_job.return_value = True
            file_model_controller.app.cache = cache
            job_dao_mock.return_value.get_job_by_id.return_value = test_job
            file_model_controller.start_download_file_dtos(
                "test_job", [file_dto_1, file_dto_2, file_dto_3]
            )
            dl.download_files.assert_called_once_with(
                "test_job", [file_dto_2, file_dto_3]
            )

    def test_stop_download_file_dtos(self, file_model_controller):
        with patch('aoget.controller.file_model_controller.get_file_model_dao'), patch(
            'aoget.controller.file_model_controller.get_job_dao'
        ) as job_dao_mock:
            test_job = Job(
                id=-1,
                name="test_job",
                status="Not Running",
                page_url="http://example.com",
                target_folder="fake_path",
            )

            file_dto_1 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name',
                name='file_name',
                status='Downloading',
                selected=False,
                size_bytes=100,
            )
            file_dto_2 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name2',
                name='file_name2',
                status='In queue',
                selected=False,
                size_bytes=100,
            )
            file_dto_3 = FileModelDTO(
                job_name='test_job',
                url='http://example.com/file_name3',
                name='file_name3',
                status='In queue',
                selected=True,
                size_bytes=100,
            )
            cache = AppCache()
            dl = MagicMock()
            file_model_controller.app.downloads = dl
            dl.is_running_for_job.return_value = True
            file_model_controller.app.cache = cache
            job_dao_mock.return_value.get_job_by_id.return_value = test_job
            file_model_controller.stop_download_file_dtos(
                "test_job", [file_dto_1, file_dto_2, file_dto_3]
            )
            dl.dequeue_files.assert_called_once_with(
                "test_job", [file_dto_2, file_dto_3]
            )
            dl.stop_active_downloads.assert_called_once_with("test_job", [file_dto_1])
