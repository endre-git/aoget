import pytest
from aoget.controller.file_details_controller import FileDetailsController


@pytest.fixture
def mock_main_window_controller(mocker):
    """Create a mock main_window_controller."""
    mock = mocker.Mock()

    # Mocking return values for get_file_dto and get_file_event_dtos
    mock.get_file_dto.return_value = mocker.Mock(
        name='TestFile',
        url='http://example.com/testfile',
        target_path='/path/to/testfile',
        size_bytes=1024,
    )

    mock_event_dto = mocker.Mock(timestamp='20210101', event='Downloaded')
    mock.get_file_event_dtos.return_value = [mock_event_dto]

    return mock


@pytest.fixture
def file_details_controller(mock_main_window_controller):
    """Create a FileDetailsController instance for the tests."""
    return FileDetailsController(
        None, mock_main_window_controller, 'job_name', 'file_name'
    )


def test_get_properties(file_details_controller):
    """Test get_properties method of FileDetailsController."""
    properties = file_details_controller.get_properties()
    assert len(properties) == 4
    assert properties["Source URL"] == 'http://example.com/testfile'
    assert properties["Target Path"] == '/path/to/testfile'
    assert (
        properties["Size"] == '1.0KB'
    )


def test_get_history_entries(file_details_controller):
    """Test get_history_entries method of FileDetailsController."""
    entries = file_details_controller.get_history_entries()
    assert entries['20210101'] == 'Downloaded'
