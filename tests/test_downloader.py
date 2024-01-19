import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from aoget.downloader.downloader import ProgressObserver, download_file, validate_file


class TestProgressObserver(ProgressObserver):
    def on_update_progress(self, written: int, total: int) -> None:
        pass


class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.url = "https://example.com/file.txt"
        self.local_path = "test_file.txt"
        self.file_size = 12

    def tearDown(self):
        file = Path(self.local_path)
        if file.exists():
            file.unlink()

    def test_download_file(self):
        progress_observer = TestProgressObserver()
        with patch("aoget.downloader.downloader.requests") as mock_requests:
            mock_head = MagicMock()
            mock_head.headers = {"content-length": str(self.file_size)}
            mock_requests.head.return_value = mock_head

            mock_get = MagicMock()
            mock_get.iter_content.return_value = [b"chunk1", b"chunk2"]
            mock_requests.get.return_value = mock_get

            download_file(self.url, self.local_path, progress_observer)

            file = Path(self.local_path)
            self.assertTrue(file.exists())
            self.assertEqual(file.stat().st_size, self.file_size)

    def test_download_file_resume(self):
        progress_observer = TestProgressObserver()
        expected_file_size = len("partial_datachunk1chunk2")
        with patch("aoget.downloader.downloader.requests") as mock_requests:
            mock_head = MagicMock()
            mock_head.headers = {
                "content-length": expected_file_size,
                "accept-ranges": "bytes",
            }
            mock_requests.head.return_value = mock_head

            mock_get = MagicMock()
            mock_get.iter_content.return_value = [b"chunk1", b"chunk2"]
            mock_requests.get.return_value = mock_get

            # Create a partially downloaded file
            file = Path(self.local_path)
            with file.open("wb") as f:
                f.write(b"partial_data")

            download_file(self.url, self.local_path, progress_observer)

            self.assertEqual(file.stat().st_size, expected_file_size)
            with file.open("rb") as f:
                self.assertEqual(f.read(), b"partial_datachunk1chunk2")

    def test_validate_file(self):
        expected_hash = (
            "e7d87b738825c33824cf3fd32b7314161fc8c425129163ff5e7260fc7288da36"
        )
        file = Path(self.local_path)
        with file.open("wb") as f:
            f.write(b"test_data")

        result = validate_file(self.local_path, expected_hash)
        self.assertTrue(result)

    def test_validate_file_invalid(self):
        expected_hash = "invalid_hash"
        file = Path(self.local_path)
        with file.open("wb") as f:
            f.write(b"test_data")

        result = validate_file(self.local_path, expected_hash)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
