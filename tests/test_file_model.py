import os
import unittest
from aoget.model.file_model import FileModel
from aoget.model.file_event import FileEvent
from aoget.model.job import Job


class TestFileModel(unittest.TestCase):
    def setUp(self):
        self.job = Job(
            name="Test Job", page_url="http://example.com", target_folder="tmp"
        )
        self.url = "https://example.com/file.txt"
        self.file_model = FileModel(self.job, self.url)

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
        file_model = FileModel(self.job, url)
        self.assertEqual(file_model.extension, "jpg")

    def test_init_without_extension(self):
        url = "https://example.com/document"
        file_model = FileModel(self.job, url)
        self.assertEqual(file_model.extension, "")

    def test_init_with_history_entry(self):
        url = "https://example.com/file.txt"
        file_model = FileModel(self.job, url)
        self.assertEqual(len(file_model.history_entries), 1)
        self.assertIsInstance(file_model.history_entries[0], FileEvent)
        self.assertEqual(file_model.history_entries[0].event, "Added.")

    def test_get_target_path(self):
        self.assertEqual(
            self.file_model.get_target_path(),
            os.path.join("tmp", "file.txt"),
        )

    def test_get_latest_history_entry(self):
        self.assertEqual(self.file_model.get_latest_history_entry().event, "Added.")

    def test_get_latest_history_timestamp(self):
        message = "Test message"
        timestamp = "2199-01-01 00:00:00"
        file_event = FileEvent(message, None)
        file_event.timestamp = timestamp
        self.file_model.history_entries.append(file_event)
        self.assertEqual(self.file_model.get_latest_history_timestamp(), timestamp)


if __name__ == "__main__":
    unittest.main()
