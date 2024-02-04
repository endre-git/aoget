import unittest
from unittest.mock import MagicMock, patch
from aoget.controller.job_editor_controller import JobEditorController


class TestJobEditorController(unittest.TestCase):

    def setUp(self):
        self.mock_job_editor_dialog = MagicMock()
        self.mock_main_window_controller = MagicMock()
        self.controller = JobEditorController(
            self.mock_job_editor_dialog, self.mock_main_window_controller, False
        )

    @patch('aoget.controller.job_editor_controller.PageCrawler')
    def test_build_fileset(self, mock_page_crawler):
        # Setting up the mock PageCrawler
        mock_page_crawler.return_value.fetch_links.return_value = {
            'pdf': ['http://example.com/file.pdf']
        }

        # Call the method under test
        result = self.controller.build_fileset('http://example.com')

        # Assertions
        self.assertIn('pdf', result)
        self.assertEqual(len(result['pdf']), 1)
        self.assertEqual(result['pdf'][0].url, 'http://example.com/file.pdf')

    def test_set_file_selected(self):
        # Setup
        self.controller.files_by_name = {'file1.pdf': MagicMock()}
        filename = 'file1.pdf'

        # Call the method under test
        self.controller.set_file_selected(filename)

        # Assertions
        self.assertTrue(self.controller.files_by_name[filename].selected)

    def test_set_file_unselected(self):
        # Setup
        self.controller.files_by_name = {'file1.pdf': MagicMock()}
        filename = 'file1.pdf'

        # Call the method under test
        self.controller.set_file_unselected(filename)

        # Assertions
        self.assertFalse(self.controller.files_by_name[filename].selected)

    # More tests can be added here for other methods like __create_job, __load_files, etc.


if __name__ == '__main__':
    unittest.main()
