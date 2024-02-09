import os
from unittest import TestCase
from unittest.mock import patch
from aoget.util.aogetutil import human_eta


class TestHistoryFunctions(TestCase):

    @patch('os.path.exists')
    def test_can_mock_builtin(self, mock_os_path_exists):
        mock_os_path_exists.return_value = True
        self.assertEqual(True, os.path.exists('lol'))

    def test_can_mock_module_function(self):
        with patch('aoget.util.aogetutil.timedelta', return_value=10):
            self.assertEqual("10", human_eta(10))
