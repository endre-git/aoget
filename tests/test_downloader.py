import unittest
import math
from unittest.mock import MagicMock, patch
from pathlib import Path
from aoget.web.downloader import DownloadSignals, download_file, validate_file


class TestProgressObserver(DownloadSignals):

    def __init__(self):
        self.rate_limit_bps = 100000

    def on_update_progress(self, written: int, total: int) -> None:
        pass

    def on_event(self, event: str) -> None:
        self.event = event


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
        with patch("aoget.web.downloader.requests") as mock_requests:
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
        with patch("aoget.web.downloader.requests") as mock_requests:
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

    def test_download_file_already_downloaded(self):
        progress_observer = TestProgressObserver()
        with patch("aoget.web.downloader.requests") as mock_requests:
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

            # Call the download_file method again
            download_file(self.url, self.local_path, progress_observer)

            # Assert that the file size is still the same
            self.assertEqual(file.stat().st_size, self.file_size)
            self.assertEqual(progress_observer.event, "File was already on disk and complete.")

    def test_five_attempts(self):
        progress_observer = TestProgressObserver()
        with patch("aoget.web.downloader.requests") as mock_requests:
            mock_head = MagicMock()
            mock_head.headers = {"content-length": str(self.file_size)}
            mock_requests.head.return_value = mock_head

            mock_get = MagicMock()
            mock_get.iter_content.return_value = [b"chunk1", b"chunk2"]
            mock_requests.get.return_value = mock_get

            # Create a partially downloaded file
            file = Path(self.local_path)
            with file.open("wb") as f:
                f.write(b"partial_data")

            # Mock the __download_attempt method to raise an exception 4 times
            with patch(
                "aoget.web.downloader.__attempt_download_file"
            ) as mock_download_attempt:
                mock_download_attempt.side_effect = [Exception("error")] * 4

                # Call the download_file method
                download_file(self.url, self.local_path, progress_observer)

                # Assert that the __download_attempt method was called 5 times
                self.assertEqual(mock_download_attempt.call_count, 5)

            # Assert that the file size is still the same as the partial download
            self.assertEqual(file.stat().st_size, len(b"partial_data"))

            # Assert that the file content is still the same as the partial download
            with file.open("rb") as f:
                self.assertEqual(f.read(), b"partial_data")

    def test_cycle_timings_1(self):
        written = 100
        chunk_size = 32
        time_to_sleep = 2
        cycles = time_to_sleep  # 2
        remaining_time = time_to_sleep
        expected_fake_written = [84, 100]
        expected_sleep_times = [0.5, 0.5]
        fake_written = []
        sleep_times = []
        for i in range(math.ceil(cycles)):
            fake_delta = (
                (i + 1) * (chunk_size / cycles)
                if cycles > 1
                else (i + 1) * (chunk_size * cycles)
            )
            fake_written.append(int(written - chunk_size + fake_delta))
            sleep_times.append(min(remaining_time, 1 / cycles))
            remaining_time -= 1 / cycles

        self.assertEqual(fake_written, expected_fake_written)
        self.assertEqual(sleep_times, expected_sleep_times)

    def test_cycle_timings_2(self):
        written = 100
        chunk_size = 32
        time_to_sleep = 3
        cycles = time_to_sleep  # 2
        remaining_time = time_to_sleep
        expected_fake_written = [78, 89, 100]
        expected_sleep_times = [1 / 3, 1 / 3, 1 / 3]
        fake_written = []
        sleep_times = []
        for i in range(math.ceil(cycles)):
            fake_delta = (
                (i + 1) * (chunk_size / cycles)
                if cycles > 1
                else (i + 1) * (chunk_size * cycles)
            )
            fake_written.append(int(written - chunk_size + fake_delta))
            sleep_times.append(min(remaining_time, 1 / cycles))
            remaining_time -= 1 / cycles

        self.assertEqual(fake_written, expected_fake_written)
        self.assertEqual(sleep_times, expected_sleep_times)

    def test_cycle_timings_3(self):
        written = 100
        chunk_size = 32
        time_to_sleep = 0.8
        cycles = time_to_sleep  # 2
        remaining_time = time_to_sleep
        expected_fake_written = [93]
        expected_sleep_times = [0.8]
        fake_written = []
        sleep_times = []
        for i in range(math.ceil(cycles)):
            fake_delta = (
                (i + 1) * (chunk_size / cycles)
                if cycles > 1
                else (i + 1) * (chunk_size * cycles)
            )
            fake_written.append(int(written - chunk_size + fake_delta))
            sleep_times.append(min(remaining_time, 1 / cycles))
            remaining_time -= 1 / cycles

        self.assertEqual(fake_written, expected_fake_written)
        self.assertEqual(sleep_times, expected_sleep_times)


if __name__ == "__main__":
    unittest.main()
