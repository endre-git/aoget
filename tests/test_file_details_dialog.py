import pytest
from PyQt6.QtWidgets import QApplication
from aoget.view.file_details_dialog import FileDetailsDialog


@pytest.fixture(scope='module')
def app():
    """Create a QApplication instance for the tests."""
    return QApplication([])


@pytest.fixture
def mock_controller(mocker):
    """Create a mock FileDetailsController."""
    mock = mocker.Mock()
    mock.get_properties.return_value = {'Property1': 'Value1', 'Property2': 'Value2'}
    mock.get_history_entries.return_value = {
        '20200112-133421332': 'Event1',
        '20200112-135121332': 'Event2',
    }
    return mock


@pytest.fixture
def dialog(mock_controller, app):
    """Create a FileDetailsDialog instance for the tests."""
    return FileDetailsDialog(None, 'job_name', 'file_name', controller=mock_controller)


def test_initialization(dialog):
    """Test the initialization of the dialog."""
    assert dialog.windowTitle() == "Details of file_name"
    assert dialog.tblFileProperties.columnCount() == 2
    assert dialog.tblFileHistory.columnCount() == 2
    assert dialog.tblFileProperties.rowCount() == 2
    assert dialog.tblFileProperties.item(0, 0).text() == "Property1"
    assert dialog.tblFileProperties.item(0, 1).text() == "Value1"
    assert dialog.tblFileHistory.rowCount() == 2
