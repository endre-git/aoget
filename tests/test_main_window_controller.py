import unittest
from unittest.mock import MagicMock
from aoget.controller.main_window_controller import MainWindowController


class TestMainWindowController(unittest.TestCase):

    def setUp(self):
        self.mock_main_window = MagicMock()
        self.mock_aoget_db = MagicMock()
        self.controller = MainWindowController(
            self.mock_main_window, self.mock_aoget_db
        )

    def test_is_file_has_history(self):
        # Create a mock job and file
        mock_job = MagicMock()
        mock_file = MagicMock()
        mock_file.has_history.return_value = True

        # Set up the controller's jobs dictionary
        self.controller.jobs = {'job1': mock_job}

        # Set up the job's get_file_by_name method to return the mock file
        mock_job.get_file_by_name.return_value = mock_file

        # Call the method under test
        result = self.controller.is_file_has_history('job1', 'file1')

        # Assert the result
        self.assertTrue(result)

        # Assert that the mock job's get_file_by_name method was called with the correct arguments
        mock_job.get_file_by_name.assert_called_once_with('file1')

        # Assert that the mock file's has_history method was called
        mock_file.has_history.assert_called_once()
    

if __name__ == '__main__':
    unittest.main()
