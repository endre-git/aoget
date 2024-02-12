import unittest
from aoget.util.aogetutil import (
    is_valid_url,
    timestamp_str,
    human_timestamp_from,
    human_filesize,
    dehumanized_filesize,
    human_eta,
    human_rate
)


class TestAogetutil(unittest.TestCase):
    def test_is_valid_url_valid(self):
        # Test case for a valid URL
        url = "https://example.com"
        result = is_valid_url(url)
        self.assertTrue(result)

    def test_is_valid_url_invalid(self):
        # Test case for an invalid URL
        url = "example.com"
        result = is_valid_url(url)
        self.assertFalse(result)

        # Test case for an empty URL
        url = ""
        result = is_valid_url(url)
        self.assertFalse(result)

        # Test case for a URL without scheme
        url = "example.com/path"
        result = is_valid_url(url)
        self.assertFalse(result)

        # Test case for a URL without netloc
        url = "https://"
        result = is_valid_url(url)
        self.assertFalse(result)

    def test_timestamp_str(self):
        # Test case for a valid timestamp string
        result = timestamp_str()
        self.assertTrue("-" in result and len(result) == 18)

    def test_human_timestamp_from(self):
        date = "20200101-000000000"
        expected_result = "2020-01-01 00:00:00"
        result = human_timestamp_from(date)
        self.assertEqual(result, expected_result)

    def test_dehumanized_filesize(self):
        # Test case for a human readable filesize of 0 bytes
        file_size_str = "0B"
        expected_result = 0
        result = dehumanized_filesize(file_size_str)
        self.assertEqual(result, expected_result)

        # Test case for a human readable filesize of 1 byte
        file_size_str = "1B"
        expected_result = 1
        result = dehumanized_filesize(file_size_str)
        self.assertEqual(result, expected_result)

        # Test case for a human readable filesize of 1 kilobyte
        file_size_str = "1KB"
        expected_result = 1024
        result = dehumanized_filesize(file_size_str)
        self.assertEqual(result, expected_result)

        # Test case for a human readable filesize of 1 megabyte
        file_size_str = "1MB"
        expected_result = 1024 * 1024
        result = dehumanized_filesize(file_size_str)
        self.assertEqual(result, expected_result)

        # Test case for a human readable filesize of 1 gigabyte
        file_size_str = "1GB"
        expected_result = 1024 * 1024 * 1024
        result = dehumanized_filesize(file_size_str)
        self.assertEqual(result, expected_result)

        # Test case for a human readable filesize of 1 terabyte
        file_size_str = "1TB"
        expected_result = 1024 * 1024 * 1024 * 1024
        result = dehumanized_filesize(file_size_str)
        self.assertEqual(result, expected_result)

        file_size_str = "14.7GB"
        expected_result = int(14.7 * 1024 * 1024 * 1024)
        result = dehumanized_filesize(file_size_str)
        self.assertEqual(result, expected_result)

    def test_human_filesize(self):
        # Test case for a filesize of 0 bytes
        file_size_bytes = 0
        expected_result = ""
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

        # Test case for a filesize of 1 byte
        file_size_bytes = 1
        expected_result = "1.0B"
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

        # Test case for a filesize of 1024 bytes
        file_size_bytes = 1024
        expected_result = "1.0KB"
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

        # Test case for a filesize of 2048 bytes
        file_size_bytes = 2048
        expected_result = "2.0KB"
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

        # Test case for a filesize of 3500 bytes
        file_size_bytes = 3500
        expected_result = "3.4KB"
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

        # Test case for a filesize of 1024 * 1024 bytes
        file_size_bytes = 1024 * 1024
        expected_result = "1.0MB"
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

        # Test case for a filesize of 1024 * 1024 * 1024 bytes
        file_size_bytes = 1024 * 1024 * 1024
        expected_result = "1.0GB"
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

        # Test case for a filesize of 1024 * 1024 * 1024 * 1024 bytes
        file_size_bytes = 1024 * 1024 * 1024 * 1024
        expected_result = "1.0TB"
        result = human_filesize(file_size_bytes)
        self.assertEqual(result, expected_result)

    def test_human_eta(self):
        # Test case for an ETA of 0 seconds
        eta_seconds = 0
        expected_result = ""
        result = human_eta(eta_seconds)
        self.assertEqual(result, expected_result)

        # Test case for an ETA of 1 second
        eta_seconds = 1
        expected_result = "0:00:01"
        result = human_eta(eta_seconds)
        self.assertEqual(result, expected_result)

        # Test case for an ETA of 60 seconds
        eta_seconds = 60
        expected_result = "0:01:00"
        result = human_eta(eta_seconds)
        self.assertEqual(result, expected_result)

        # Test case for an ETA of 3600 seconds
        eta_seconds = 3600
        expected_result = "1:00:00"
        result = human_eta(eta_seconds)
        self.assertEqual(result, expected_result)

        # Test case for an ETA of 86400 seconds
        eta_seconds = 86400
        expected_result = "1 day, 0:00:00"
        result = human_eta(eta_seconds)
        self.assertEqual(result, expected_result)

    def test_human_rate(self):
        # Test case for a rate of 0 bytes per second
        rate_bytes_per_second = 0
        expected_result = ""
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)

        # Test case for a rate of 1 byte per second
        rate_bytes_per_second = 1
        expected_result = "1.0B/s"
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)

        # Test case for a rate of 1024 bytes per second
        rate_bytes_per_second = 1024
        expected_result = "1.0KB/s"
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)

        # Test case for a rate of 2048 bytes per second
        rate_bytes_per_second = 2048
        expected_result = "2.0KB/s"
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)

        # Test case for a rate of 3500 bytes per second
        rate_bytes_per_second = 3500
        expected_result = "3.4KB/s"
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)

        # Test case for a rate of 1024 * 1024 bytes per second
        rate_bytes_per_second = 1024 * 1024
        expected_result = "1.0MB/s"
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)

        # Test case for a rate of 1024 * 1024 * 1024 bytes per second
        rate_bytes_per_second = 1024 * 1024 * 1024
        expected_result = "1.0GB/s"
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)

        # Test case for a rate of 1024 * 1024 * 1024 * 1024 bytes per second
        rate_bytes_per_second = 1024 * 1024 * 1024 * 1024
        expected_result = "1.0TB/s"
        result = human_rate(rate_bytes_per_second)
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
