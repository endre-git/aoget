import unittest
from aoget.model.file_event import FileEvent
from aoget.model.file_model import FileModel
from aoget.model.job import Job


class TestFileEvent(unittest.TestCase):

    def setUp(self):
        self.test_file = FileModel(
            Job(
                name="Test Job", page_url="http://example.com", target_folder="/tmp"
            ),
            "https://example.com/file.txt",
        )

    def test_file_event_init(self):
        # Test case for initializing FileEvent
        message = "Test message"
        file_event = FileEvent(message, self.test_file)
        self.assertEqual(file_event.event, message)
        self.assertIsNotNone(file_event.timestamp)

    def test_file_event_repr(self):
        # Test case for __repr__ method of FileEvent
        message = "Test message"
        timestamp = "2022-01-01 00:00:00"
        file_event = FileEvent(message, self.test_file)
        file_event.timestamp = timestamp
        expected_repr = (
            "<FileEvent(timestamp='2022-01-01 00:00:00', event='Test message')>"
        )
        self.assertEqual(repr(file_event), expected_repr)


if __name__ == "__main__":
    unittest.main()
