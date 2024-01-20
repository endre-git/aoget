import unittest
from urllib.parse import unquote
from aoget.model.file_model import FileModel, FileEvent


class TestFileModel(unittest.TestCase):
    def setUp(self):
        self.url = "https://example.com/file.txt"
        self.file_model = FileModel(self.url)

    def test_init(self):
        self.assertEqual(self.file_model.url, self.url)
        self.assertEqual(self.file_model.status, FileModel.STATUS_NEW)
        self.assertEqual(self.file_model.name, "file.txt")
        self.assertEqual(self.file_model.extension, "txt")

    def test_repr(self):
        expected_repr = (
            "<FileModel(name='file.txt', url='https://example.com/file.txt')>"
        )
        self.assertEqual(repr(self.file_model), expected_repr)

    def test_init_with_extension(self):
        url = "https://example.com/image.jpg"
        file_model = FileModel(url)
        self.assertEqual(file_model.extension, "jpg")

    def test_init_without_extension(self):
        url = "https://example.com/document"
        file_model = FileModel(url)
        self.assertEqual(file_model.extension, "")

    def test_init_with_history_entry(self):
        url = "https://example.com/file.txt"
        file_model = FileModel(url)
        self.assertEqual(len(file_model.history_entries), 1)
        self.assertIsInstance(file_model.history_entries[0], FileEvent)
        self.assertEqual(file_model.history_entries[0].event_type, "Parsed from page")

if __name__ == "__main__":
    unittest.main()