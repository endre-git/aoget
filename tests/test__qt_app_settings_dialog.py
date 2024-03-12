import os
import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from aoget.view.app_settings_dialog import AppSettingsDialog
from aoget.config.app_config import AppConfig
from PyQt6.QtWidgets import QDialogButtonBox


class TestAppSettingsDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def setUp(self):
        self.dialog = AppSettingsDialog()

    def test_setup_ui(self):
        # setup UI is implicit with construction, so no need to explicitly call it

        # Check if UI elements are initialized correctly
        self.assertEqual(self.dialog.cmbJobNaming.count(), 3)
        self.assertEqual(self.dialog.cmbJobFolders.count(), 2)

    @patch("aoget.view.app_settings_dialog.set_config_value")
    def test_controls(self, mock_set_config_value):
        current_dir_abs_path = os.path.abspath(os.path.dirname(__file__))

        # target folder - incorrectly set -> no change in config
        self.dialog.txtTargetFolder.setText("")
        mock_set_config_value.assert_not_called()

        # target folder - correctly set
        self.dialog.txtTargetFolder.setText(current_dir_abs_path)
        mock_set_config_value.assert_called_with(
            AppConfig.DEFAULT_DOWNLOAD_FOLDER, current_dir_abs_path
        )

    @patch("aoget.view.app_settings_dialog.save_config_to_file")
    def test_on_ok_clicked(self, mock_save_config_to_file):
        self.dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok).click()
        mock_save_config_to_file.assert_called()

    @patch("aoget.view.app_settings_dialog.save_config_to_file")
    def test_on_cancel_clicked(self, mock_save_config_to_file):
        self.dialog.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).click()
        mock_save_config_to_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
