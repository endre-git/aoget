import unittest
import aoget.config.app_config as app_config
from aoget.config.app_config import AppConfig
import json
import os
import tempfile


class TestAppConfig(unittest.TestCase):

    def test_get_app_version(self):
        version = app_config.get_app_version()
        self.assertEqual(version, "0.9.1")

    def test_get_config_value(self):
        value = app_config.get_config_value(AppConfig.DEBUG)
        self.assertFalse(value)

    def test_load_config_from_file(self):
        filename = "test_config.json"
        temp_dir = os.path.abspath(tempfile.gettempdir())
        filename = os.path.join(temp_dir, filename)
        settings_folder = os.path.join(temp_dir, "test_settings")
        downloads_folder = os.path.join(temp_dir, "test_downloads_folder")
        config = {
            AppConfig.DEBUG: True,
            AppConfig.SETTINGS_FOLDER: settings_folder,
            AppConfig.DEFAULT_DOWNLOAD_FOLDER: downloads_folder,
        }
        with open(filename, "w") as file:
            file.write(json.dumps(config))
        app_config.load_config_from_file(filename)
        self.assertEqual(app_config.get_config_value(AppConfig.DEBUG), True)
        self.assertEqual(
            app_config.get_config_value(AppConfig.SETTINGS_FOLDER), settings_folder
        )
        os.remove(filename)

    def test_if_no_download_folder_a_default_will_be_used(self):
        filename = "test_config.json"
        temp_dir = os.path.abspath(tempfile.gettempdir())
        filename = os.path.join(temp_dir, filename)
        settings_folder = os.path.join(temp_dir, "test_settings")
        config = {
            AppConfig.DEBUG: True,
            AppConfig.SETTINGS_FOLDER: settings_folder,
            AppConfig.DEFAULT_DOWNLOAD_FOLDER: "",
        }
        with open(filename, "w") as file:
            file.write(json.dumps(config))
        app_config.load_config_from_file(filename)
        self.assertEqual(app_config.get_config_value(AppConfig.DEBUG), True)
        self.assertEqual(
            app_config.get_config_value(AppConfig.SETTINGS_FOLDER), settings_folder
        )
        
        default_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        default_folder_existed_before_test = os.path.exists(default_folder)

        self.assertEqual(
            app_config.get_config_value(AppConfig.DEFAULT_DOWNLOAD_FOLDER),
            default_folder,
        )
        os.remove(filename)
        if not default_folder_existed_before_test:
            os.rmdir(default_folder)

    def test_load_config_from_file_file_not_found(self):
        filename = "test_config.json"
        temp_dir = os.path.abspath(tempfile.gettempdir())
        filename = os.path.join(temp_dir, filename)
        with self.assertRaises(FileNotFoundError):
            app_config.load_config_from_file(filename)

    def test_load_config_from_file_invalid_json(self):
        filename = "test_config.json"
        temp_dir = os.path.abspath(tempfile.gettempdir())
        filename = os.path.join(temp_dir, filename)
        with open(filename, "w") as file:
            file.write("invalid_json")
        with self.assertRaises(json.JSONDecodeError):
            app_config.load_config_from_file(filename)
        os.remove(filename)

    def test_validate_bandwidth_settings(self):
        filename = "test_config.json"
        temp_dir = os.path.abspath(tempfile.gettempdir())
        filename = os.path.join(temp_dir, filename)
        settings_folder = os.path.join(temp_dir, "test_settings")
        downloads_folder = os.path.join(temp_dir, "test_downloads_folder")
        config = {
            AppConfig.DEBUG: True,
            AppConfig.SETTINGS_FOLDER: settings_folder,
            AppConfig.DEFAULT_DOWNLOAD_FOLDER: downloads_folder,
        }
        with open(filename, "w") as file:
            file.write(json.dumps(config))
        app_config.load_config_from_file(filename)
        self.assertEqual(app_config.get_config_value(AppConfig.DEBUG), True)
        self.assertEqual(
            app_config.get_config_value(AppConfig.SETTINGS_FOLDER), settings_folder
        )
        self.assertEqual(
            app_config.get_config_value(AppConfig.HIGH_BANDWIDTH_LIMIT), 5000
        )
        os.remove(filename)

    def test_validate_bandwidth_settings_not_a_number(self):
        filename = "test_config.json"
        temp_dir = os.path.abspath(tempfile.gettempdir())
        filename = os.path.join(temp_dir, filename)
        settings_folder = os.path.join(temp_dir, "test_settings")
        downloads_folder = os.path.join(temp_dir, "test_downloads_folder")
        config = {
            AppConfig.DEBUG: True,
            AppConfig.SETTINGS_FOLDER: settings_folder,
            AppConfig.DEFAULT_DOWNLOAD_FOLDER: downloads_folder,
            AppConfig.HIGH_BANDWIDTH_LIMIT: "not_a_number",
        }
        with open(filename, "w") as file:
            file.write(json.dumps(config))
        with self.assertRaises(Exception):
            app_config.load_config_from_file(filename)
        os.remove(filename)

        
if __name__ == "__main__":
    unittest.main()
