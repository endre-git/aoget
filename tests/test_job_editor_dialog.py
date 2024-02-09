import pytest
import unittest
from unittest.mock import patch, MagicMock
from aoget.view.job_editor_dialog import JobEditorDialog


class TestJobEditorDialog(unittest.TestCase):

    @pytest.mark.skip(reason="Windows crashes when uic.load happens, and I don't know why")
    @patch(
        'aoget.view.job_editor_dialog.aogetsettings.get_url_history',
        return_value=["http://example.com"],
    )
    @patch(
        'aoget.view.job_editor_dialog.aogetsettings.get_target_folder_history',
        return_value=["/path/to/folder"],
    )
    def test_init(self, mock_get_target_folder_history, mock_get_url_history):
        # Mock the main window controller and JobEditorController
        mock_main_window_controller = MagicMock()
        mock_job_editor_controller = MagicMock()
        with patch(
            'aoget.view.job_editor_dialog.JobEditorController',
            return_value=mock_job_editor_controller,
        ):
            dialog = JobEditorDialog(
                main_window_controller=mock_main_window_controller, job_name="TestJob"
            )

            # Assertions to validate the initialization
            self.assertEqual(dialog.job_name_unique, True)
            self.assertIsInstance(dialog.controller, MagicMock)  # Since it's mocked



if __name__ == '__main__':
    unittest.main()
