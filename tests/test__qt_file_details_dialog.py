import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from aoget.view.file_details_dialog import FileDetailsDialog


class TestFileDetailsDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def setUp(self):
        mock = MagicMock()
        mock.get_properties.return_value = {
            'Property1': 'Value1',
            'Property2': 'Value2',
        }
        mock.get_history_entries.return_value = {
            '20200112-133421332': 'Event1',
            '20200112-135121332': 'Event2',
        }
        self.dialog = FileDetailsDialog(None, "job_name", "file_name", mock)

    def test_initialization(self):
        assert self.dialog.windowTitle() == "Details of file_name"
        assert self.dialog.tblFileProperties.columnCount() == 2
        assert self.dialog.tblFileHistory.columnCount() == 2
        assert self.dialog.tblFileProperties.rowCount() == 2
        assert self.dialog.tblFileProperties.item(0, 0).text() == "Property1"
        assert self.dialog.tblFileProperties.item(0, 1).text() == "Value1"
        assert self.dialog.tblFileHistory.rowCount() == 2


if __name__ == '__main__':
    unittest.main()
