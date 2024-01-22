import unittest
from aoget.util.aogetutil import is_valid_url, timestamp_str, human_timestamp_from, human_filesize


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
        self.assertTrue("-" in result and len(result) == 15)

    def test_human_timestamp_from(self):
        date = "20200101-000000"
        expected_result = "2020-01-01 00:00:00"
        result = human_timestamp_from(date)
        self.assertEqual(result, expected_result)

    def test_human_filesize(self):
        # Test case for a filesize of 0 bytes
        file_size_bytes = 0
        expected_result = "0B"
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
        

if __name__ == "__main__":
    unittest.main()
