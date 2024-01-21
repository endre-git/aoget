import unittest
from unittest.mock import MagicMock
from aoget.model.file_event import FileEvent
from aoget.model.file_model import FileModel
from aoget.model.job import Job

class TestJob(unittest.TestCase):
    def setUp(self):
        self.job = Job()
        self.file1 = FileModel("https://example.com/file1.txt")
        self.file2 = FileModel("https://example.com/file2.txt")
        self.job.files = [self.file1, self.file2]

    def test_len(self):
        self.assertEqual(len(self.job), 0)  # none selected = 0
        self.job.set_file_selected("file1.txt")
        self.assertEqual(len(self.job), 1)  # 1 selected = 1

    def test_ingest_links(self):
        ao_page = MagicMock()
        ao_page.files_by_extension = {
            "txt": ["https://example.com/file3.txt", "https://example.com/file4.txt"],
            "jpg": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
        }
        self.job.ingest_links(ao_page)
        self.assertEqual(len(self.job.files), 6)  # during setup we already add two files

    def test_resolve_files_to_download(self):
        # select both files for download
        self.job.set_file_selected("file1.txt")
        self.job.set_file_selected("file2.txt")
        self.job.target_folder = "/tmp"
        # Mocking os.path.isfile to return True for file1 and False for file2
        with unittest.mock.patch("os.path.isfile") as mock_isfile:
            mock_isfile.side_effect = [True, False]
            files_to_download = self.job.resolve_files_to_download()
            self.assertEqual(len(files_to_download), 1)
            self.assertEqual(files_to_download[0], self.file2)

    def test_set_files(self):
        filemodels = [FileModel("https://example.com/file3.txt"), FileModel("https://example.com/file4.txt")]
        self.job.set_files(filemodels)
        self.assertEqual(self.job.files, filemodels)

    def test_get_sorted_extensions(self):
        extensions = self.job.get_sorted_extensions()
        self.assertEqual(extensions, ["txt"])

    def test_get_sorted_filenames_by_extension(self):
        filenames = self.job.get_sorted_filenames_by_extension("txt")
        self.assertEqual(filenames, ["file1.txt", "file2.txt"])

    def test_set_file_selected(self):
        self.job.set_file_selected("file1.txt")
        self.assertTrue(self.file1.selected)

    def test_set_file_unselected(self):
        self.job.set_file_unselected("file1.txt")
        self.assertFalse(self.file1.selected)

    def test_get_selected_filenames(self):
        self.file1.selected = True
        self.file2.selected = True
        selected_filenames = self.job.get_selected_filenames()
        self.assertEqual(selected_filenames, ["file1.txt", "file2.txt"])

    def test_get_file_by_name(self):
        file = self.job.get_file_by_name("file1.txt")
        self.assertEqual(file, self.file1)

if __name__ == "__main__":
    unittest.main()