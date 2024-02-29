import unittest
from aoget.controller.app_cache import AppCache


class TestAppCache(unittest.TestCase):

    def setUp(self):
        self.app_cache = AppCache()

    def test_drop_file_existing_job_and_file(self):
        job_name = "Test Job"
        file_name = "test_file.txt"
        self.app_cache.file_dto_cache[job_name] = {file_name: "file_data"}
        self.app_cache.drop_file(job_name, file_name)
        self.assertNotIn(file_name, self.app_cache.file_dto_cache[job_name])

    def test_drop_file_existing_job_and_nonexistent_file(self):
        job_name = "Test Job"
        file_name = "nonexistent_file.txt"
        self.app_cache.file_dto_cache[job_name] = {"test_file.txt": "file_data"}
        self.app_cache.drop_file(job_name, file_name)
        self.assertIn("test_file.txt", self.app_cache.file_dto_cache[job_name])

    def test_drop_file_nonexistent_job(self):
        job_name = "Nonexistent Job"
        file_name = "test_file.txt"
        self.app_cache.drop_file(job_name, file_name)
        self.assertNotIn(job_name, self.app_cache.file_dto_cache)

    def test_drop_job_existing_job(self):
        job_name = "Test Job"
        self.app_cache.file_dto_cache[job_name] = {"test_file.txt": "file_data"}
        self.app_cache.drop_job(job_name)
        self.assertNotIn(job_name, self.app_cache.file_dto_cache)

    def test_drop_job_nonexistent_job(self):
        job_name = "Nonexistent Job"
        self.app_cache.drop_job(job_name)
        self.assertNotIn(job_name, self.app_cache.file_dto_cache)


if __name__ == "__main__":
    unittest.main()
