import unittest
from aoget.util.aogetutil import is_valid_url, timestamp_str, human_timestamp_from


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
        

if __name__ == "__main__":
    unittest.main()
