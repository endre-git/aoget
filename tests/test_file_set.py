import unittest
from aoget.model.file_set import FileSet
from aoget.model.file_model import FileModel
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()


def create_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


class TestFileSet(unittest.TestCase):
    def setUp(self):
        create_test_session()
        self.file_set = FileSet()

    def test_set_files(self):
        filemodels = [
            FileModel("https://site.com/file1.txt"),
            FileModel("https://site.com/file%202.txt"),
            FileModel("https://site.com/file3.csv"),
            FileModel("https://site.com/file4.csv"),
            FileModel("https://site.com/image1.jpg"),
            FileModel("https://site.com/image2.jpg"),
        ]
        self.file_set.set_files(filemodels)

        expected_files = {
            "file1.txt": filemodels[0],
            "file 2.txt": filemodels[1],
            "file3.csv": filemodels[2],
            "file4.csv": filemodels[3],
            "image1.jpg": filemodels[4],
            "image2.jpg": filemodels[5],
        }
        self.assertEqual(self.file_set.files, expected_files)

        expected_files_by_extension = {
            "txt": [filemodels[0], filemodels[1]],
            "csv": [filemodels[2], filemodels[3]],
            "jpg": [filemodels[4], filemodels[5]],
        }
        self.assertEqual(self.file_set.files_by_extension, expected_files_by_extension)

    def test_get_sorted_extensions(self):
        self.file_set.files_by_extension = {"txt": [], "csv": [], "jpg": []}
        expected_result = ["csv", "jpg", "txt"]
        result = self.file_set.get_sorted_extensions()
        self.assertEqual(result, expected_result)

    def test_get_sorted_filenames_by_extension(self):
        self.file_set.files_by_extension = {
            "txt": [FileModel("file1.txt"), FileModel("file2.txt")],
            "csv": [FileModel("file3.csv"), FileModel("file4.csv")],
            "jpg": [FileModel("image1.jpg"), FileModel("image2.jpg")],
        }

        # Test case for extension 'txt'
        extension = "txt"
        expected_result = ["file1.txt", "file2.txt"]
        result = self.file_set.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

        # Test case for extension 'csv'
        extension = "csv"
        expected_result = ["file3.csv", "file4.csv"]
        result = self.file_set.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

        # Test case for extension 'jpg'
        extension = "jpg"
        expected_result = ["image1.jpg", "image2.jpg"]
        result = self.file_set.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

        # Test case for extension 'pdf' (non-existent extension)
        extension = "pdf"
        expected_result = []
        result = self.file_set.get_sorted_filenames_by_extension(extension)
        self.assertEqual(result, expected_result)

    def test_set_selected(self):
        filemodel = FileModel("file1.txt")
        self.file_set.files = {"file1.txt": filemodel}

        self.file_set.set_selected("file1.txt")
        self.assertTrue(filemodel.selected)

    def test_set_unselected(self):
        filemodel = FileModel("file1.txt")
        filemodel.selected = True
        self.file_set.files = {"file1.txt": filemodel}

        self.file_set.set_unselected("file1.txt")
        self.assertFalse(filemodel.selected)

    def test_get_selected_filenames(self):
        filemodels = [
            FileModel("https://site.com/file1.txt"),
            FileModel("https://site.com/file%202.txt"),
            FileModel("https://site.com/file3.csv"),
            FileModel("https://site.com/file4.csv"),
            FileModel("https://site.com/image1.jpg"),
            FileModel("https://site.com/image2.jpg"),
        ]
        for filemodel in filemodels:
            filemodel.selected = True
        self.file_set.files = {
            "file1.txt": filemodels[0],
            "file 2.txt": filemodels[1],
            "file3.csv": filemodels[2],
            "file4.csv": filemodels[3],
            "image1.jpg": filemodels[4],
            "image2.jpg": filemodels[5],
        }

        expected_result = [
            "file 2.txt",
            "file1.txt",
            "file3.csv",
            "file4.csv",
            "image1.jpg",
            "image2.jpg",
        ]
        result = self.file_set.get_selected_filenames()
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
