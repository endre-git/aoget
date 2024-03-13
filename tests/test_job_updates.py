import unittest
from aoget.model.job_updates import JobUpdates, JobDTO, FileModelDTO


class TestJobUpdates(unittest.TestCase):
    def setUp(self):
        self.job_updates = JobUpdates("test_job")

    def tearDown(self):
        self.job_updates.clear()

    def test_add_job_update(self):
        job_dto = JobDTO(
            id=1, name="test_job", page_url="http://example.com", status="running"
        )
        self.job_updates.add_job_update(job_dto)
        self.assertEqual(self.job_updates.job_update, job_dto)

    def test_update_job_threads(self):
        self.job_updates.update_job_threads(5, 3)
        self.assertEqual(self.job_updates.job_update.threads_allocated, 5)
        self.assertEqual(self.job_updates.job_update.threads_active, 3)

    def test_update_job_downloaded_bytes(self):
        self.job_updates.update_job_downloaded_bytes(1000)
        self.assertEqual(self.job_updates.job_update.downloaded_bytes, 1000)

    def test_update_job_files_done(self):
        self.job_updates.update_job_files_done(10)
        self.assertEqual(self.job_updates.job_update.files_done, 10)

    def test_add_file_model_update(self):
        file_model_dto = FileModelDTO(
            job_name="test_job", name="file1.txt", size_bytes=100
        )
        self.job_updates.add_file_model_update(file_model_dto)
        self.assertEqual(
            self.job_updates.file_model_updates["file1.txt"], file_model_dto
        )

    def test_incremental_job_update(self):
        job_dto = JobDTO(id=1, name="test_job", status="completed")
        self.job_updates.incremental_job_update(job_dto)
        self.assertEqual(self.job_updates.job_update.status, "completed")

    def test_incremental_file_model_update(self):
        file_model_dto = FileModelDTO(
            job_name="test_job", name="file1.txt", size_bytes=200
        )
        self.job_updates.incremental_file_model_update(file_model_dto)
        self.assertEqual(
            self.job_updates.file_model_updates["file1.txt"].size_bytes, 200
        )

    def test_add_file_event(self):
        self.job_updates.add_file_event("file1.txt", "Completed downloading.")
        self.assertEqual(len(self.job_updates.file_event_updates["file1.txt"]), 1)

    def test_add_file_events(self):
        events = {
            "file1.txt": "Started downloading.",
            "file2.txt": "Completed downloading.",
        }
        self.job_updates.add_file_events(events)
        self.assertEqual(len(self.job_updates.file_event_updates["file1.txt"]), 1)
        self.assertEqual(len(self.job_updates.file_event_updates["file2.txt"]), 1)

    def test_update_file_download_progress(self):
        self.job_updates.update_file_download_progress("file1.txt", 500, 1000)
        self.assertEqual(
            self.job_updates.file_model_updates["file1.txt"].downloaded_bytes, 500
        )
        self.assertEqual(
            self.job_updates.file_model_updates["file1.txt"].size_bytes, 1000
        )

    def test_update_file_status(self):
        self.job_updates.update_file_status("file1.txt", "Completed")
        self.assertEqual(
            self.job_updates.file_model_updates["file1.txt"].status, "Completed"
        )
        self.assertEqual(len(self.job_updates.file_event_updates["file1.txt"]), 1)
        self.assertEqual(
            self.job_updates.file_event_updates["file1.txt"][0].event,
            "Completed downloading.",
        )

    def test_merge_file_size_in_second(self):
        job_updates_1 = JobUpdates("test_job")
        job_updates_2 = JobUpdates("test_job")
        job_updates_2.update_file_size("file1.txt", 1000)
        job_updates_1.merge(job_updates_2)
        assert job_updates_1.file_model_updates["file1.txt"].size_bytes == 1000

    def test_merge_file_size_for_existing_file(self):
        job_updates_1 = JobUpdates("test_job")
        job_updates_2 = JobUpdates("test_job")
        job_updates_1.update_file_status("file1.txt", "Completed")
        job_updates_2.update_file_size("file1.txt", 1000)
        job_updates_1.merge(job_updates_2)
        assert job_updates_1.file_model_updates["file1.txt"].size_bytes == 1000
        assert job_updates_1.file_model_updates["file1.txt"].status == "Completed"


if __name__ == "__main__":
    unittest.main()
