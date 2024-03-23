import unittest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from aoget.view.login_dialog import LoginDialog


class TestLoginDialog(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def test_init(self):
        with patch("aoget.view.login_dialog.EmbeddedBrowser") as mock_browser:
            LoginDialog()
            mock_browser.assert_called_once()
            mock_browser.return_value.load.assert_called_once_with(
                "https://archive.org/account/login"
            )


if __name__ == "__main__":
    unittest.main()
