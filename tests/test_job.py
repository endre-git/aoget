import os
import unittest
from unittest.mock import MagicMock
from aoget.model.file_model import FileModel
from aoget.model.job import Job


class TestJob(unittest.TestCase):
    def setUp(self):
        self.job = Job(
            name='Test Job', page_url='http://example.com', target_folder='tmp'
        )
        self.file1 = FileModel(self.job, "https://example.com/file1.txt")
        self.file2 = FileModel(self.job, "https://example.com/file2.txt")
        self.job.files = [self.file1, self.file2]

    def tearDown(self) -> None:
        return super().tearDown()

    def test_len(self):
        self.assertEqual(len(self.job), 0)  # none selected = 0
        self.job.set_file_selected("file1.txt")
        self.assertEqual(len(self.job), 1)  # 1 selected = 1


    def test_set_files(self):
        filemodels = [
            FileModel(self.job, "https://example.com/file3.txt"),
            FileModel(self.job, "https://example.com/file4.txt"),
        ]
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

    def test_get_file_by_name_not_found(self):
        file = self.job.get_file_by_name("file3.txt")
        self.assertIsNone(file)

    def test_add_file(self):
        file = FileModel(self.job, "https://example.com/file3.txt")
        self.job.add_file(file)
        self.assertEqual(len(self.job.files), 3)
        self.assertEqual(self.job.files[2], file)
        self.assertEqual(self.job.files[2].get_target_path(),
                         os.path.join("tmp", "file3.txt"))

    def test_get_selected_files_with_unknown_size(self):
        self.file1.selected = True
        self.file2.selected = True
        self.file1.size_bytes = 0
        self.file2.size_bytes = 100
        files = self.job.get_selected_files_with_unknown_size()
        self.assertEqual(files, [self.file1])


if __name__ == "__main__":
    unittest.main()
