import unittest
from aoget.model.dto.job_dto import JobDTO


class TestJobDTO(unittest.TestCase):

    def test_merge(self):
        job = JobDTO(
            id=-1,
            name="Test Job",
            status="Not Running",
            page_url="http://test.com",
            total_size_bytes=123123123,
            target_folder="/path/to/folder",
            downloaded_bytes=0,
            selected_files_count=0,
            selected_files_with_known_size=0,
            threads_allocated=1,
            files_done=0,
        )

        updated_job = JobDTO(
            id=-1,
            name="Updated Job",
            status="Running",
            page_url="http://updated.com",
            total_size_bytes=456456456,
            target_folder="/path/to/updated/folder",
            downloaded_bytes=100,
            selected_files_count=10,
            selected_files_with_known_size=5,
            threads_allocated=2,
            files_done=5,
        )

        job.merge(updated_job)

        self.assertEqual(job.name, "Updated Job")
        self.assertEqual(job.status, "Running")
        self.assertEqual(job.page_url, "http://updated.com")
        self.assertEqual(job.total_size_bytes, 456456456)
        self.assertEqual(job.target_folder, "/path/to/updated/folder")
        self.assertEqual(job.downloaded_bytes, 100)
        self.assertEqual(job.selected_files_count, 10)
        self.assertEqual(job.selected_files_with_known_size, 5)
        self.assertEqual(job.threads_allocated, 2)
        self.assertEqual(job.files_done, 5)


if __name__ == "__main__":
    unittest.main()
