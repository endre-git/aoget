import unittest
import urllib.parse
from aoget.web.aopage import AoPage


class TestAopage(unittest.TestCase):
    def setUp(self):
        self.aopage = AoPage()
        self.aopage.files_by_extension = {
            "txt": [
                "https://example.com/file1.txt",
                "https://example.com/file2.txt",
                "https://example.com/file%20name2.txt",
            ],
            "csv": ["https://example.com/file3.csv", "https://example.com/file4.csv"],
            "jpg": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
        }

    def test_get_sorted_filenames_by_extension(self):
        # Test case for extension 'txt'
        extension = "txt"
        expected_result = ["file name2.txt", "file1.txt", "file2.txt"]
        result = self.aopage.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

        # Test case for extension 'csv'
        extension = "csv"
        expected_result = ["file3.csv", "file4.csv"]
        result = self.aopage.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

        # Test case for extension 'jpg'
        extension = "jpg"
        expected_result = ["image1.jpg", "image2.jpg"]
        result = self.aopage.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

        # Test case for extension 'pdf' (non-existent extension)
        extension = "pdf"
        expected_result = []
        result = self.aopage.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

    def test_get_sorted_extensions(self):
        expected_result = ["csv", "jpg", "txt"]
        result = self.aopage.get_sorted_extensions()
        self.assertEqual(result, expected_result)

    def test_unescape(self):
        expected_result = "file name2.txt"
        result = urllib.parse.unquote("file%20name2.txt")
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
