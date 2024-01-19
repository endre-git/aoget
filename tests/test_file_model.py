import unittest
from aoget.model.file_model import FileModel


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


if __name__ == "__main__":
    unittest.main()
