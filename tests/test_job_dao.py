import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from aoget.model.job import Job
from aoget.model.dao.job_dao import JobDAO


class TestJobDAO(unittest.TestCase):
    def setUp(self):
        # Create an SQLite in-memory database for testing
        self.engine = create_engine('sqlite:///:memory:')
        self.session = Session(self.engine)

        # Create the tables in the database
        Job.metadata.create_all(self.engine)

        # Create an instance of JobDAO with the testing session
        self.job_dao = JobDAO(self.session)

    def tearDown(self):
        # Close the session and dispose of the engine after each test
        self.session.close()
        self.engine.dispose()

    def test_create_save_retrieve_job(self):
        # Create a new job
        new_job = Job(
            name='Test Job', page_url='http://example.com', target_folder='/tmp'
        )

        # Save the job using save_job method
        self.job_dao.add_job(new_job)

        # Retrieve the job by its ID
        retrieved_job = self.job_dao.get_job_by_id(new_job.id)

        # Assert that the retrieved job matches the created job
        self.assertEqual(retrieved_job.name, 'Test Job')
        self.assertEqual(retrieved_job.page_url, 'http://example.com')
        self.assertEqual(retrieved_job.target_folder, '/tmp')

    def test_get_all_jobs(self):
        # Create multiple jobs
        self.job_dao.create_job(
            name='Job 1', page_url='http://example.com', target_folder='/tmp'
        )
        self.job_dao.create_job(
            name='Job 2', page_url='http://example.com', target_folder='/tmp'
        )
        self.job_dao.create_job(
            name='Job 3', page_url='http://example.com', target_folder='/tmp'
        )

        # Retrieve all jobs
        jobs = self.job_dao.get_all_jobs()

        # Assert that the correct number of jobs is retrieved
        self.assertEqual(len(jobs), 3)

    def test_delete_job_by_id(self):
        # Create a job
        new_job = Job(
            name='Test Job', page_url='http://example.com', target_folder='/tmp'
        )

        # Save the job using save_job method
        self.job_dao.add_job(new_job)
        self.assertNotEqual(0, new_job.id)
        new_job_id = new_job.id

        # Delete the job by its ID
        self.job_dao.delete_job_by_id(new_job.id)

        # Assert that the job is deleted
        self.assertIsNone(self.job_dao.get_job_by_id(new_job_id))

    def test_delete_all_jobs(self):
        # Create multiple jobs
        self.job_dao.create_job(
            name='Job 1', page_url='http://example.com', target_folder='/tmp'
        )
        self.job_dao.create_job(
            name='Job 2', page_url='http://example.com', target_folder='/tmp'
        )
        self.job_dao.create_job(
            name='Job 3', page_url='http://example.com', target_folder='/tmp'
        )

        # Delete all jobs
        self.job_dao.delete_all_jobs()

        # Assert that no jobs are left
        self.assertEqual(len(self.job_dao.get_all_jobs()), 0)

if __name__ == '__main__':
    unittest.main()
