import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from aoget.model.file_model import FileModel
from aoget.model.dao.file_model_dao import FileModelDAO
from aoget.model.dao.job_dao import JobDAO
from aoget.model.dao.file_event_dao import FileEventDAO


class TestFileModelDAO(unittest.TestCase):
    def setUp(self):
        # Create an SQLite in-memory database for testing
        self.engine = create_engine('sqlite:///:memory:')
        self.session = Session(self.engine)

        # Create the tables in the database
        FileModel.metadata.create_all(self.engine)

        # Create an instance of FileModelDAO with the testing session
        self.file_model_dao = FileModelDAO(self.session)
        self.file_event_dao = FileEventDAO(self.session)

        # Files can't exist without a job, so we need to create a job
        self.job_dao = JobDAO(self.session)
        self.job = self.job_dao.create_job(
            name='Test Job', page_url='http://example.com', target_folder='/tmp'
        )

    def tearDown(self):
        # Close the session and dispose of the engine after each test
        self.session.close()
        self.engine.dispose()

    def test_create_file_model(self):
        # Create a new file model using create_file_model method
        new_file_model = self.file_model_dao.create_file_model(
            job=self.job,
            url='http://example.com/file1.txt'
        )

        self.assertNotEqual(0, new_file_model.id)

        # Retrieve the file model by its ID
        retrieved_file_model = self.file_model_dao.get_file_model_by_id(
            new_file_model.id
        )

        # Assert that the retrieved file model matches the created file model
        self.assertEqual(retrieved_file_model.url, 'http://example.com/file1.txt')

    def test_add_file_model(self):
        # Create a new file model
        new_file_model = self.file_model_dao.create_file_model(
            job=self.job,
            url='http://example.com/file1.txt'
        )

        # Add the file model using add_file_model method
        self.file_model_dao.add_file_model(new_file_model)

        # Retrieve the file model by its ID
        retrieved_file_model = self.file_model_dao.get_file_model_by_id(
            new_file_model.id
        )

        # Assert that the retrieved file model matches the added file model
        self.assertEqual(retrieved_file_model.url, 'http://example.com/file1.txt')

    def test_get_file_model_by_id(self):
        # Create a new file model and retrieve it by ID
        new_file_model = self.file_model_dao.create_file_model(
            job=self.job,
            url='http://example.com/file1.txt'
        )
        retrieved_file_model = self.file_model_dao.get_file_model_by_id(
            new_file_model.id
        )

        # Assert that the retrieved file model matches the created file model
        self.assertEqual(retrieved_file_model.url, 'http://example.com/file1.txt')

    def test_get_all_file_models(self):
        # Create multiple file models
        self.file_model_dao.create_file_model(url='http://example.com/file1.txt', job=self.job)
        self.file_model_dao.create_file_model(url='http://example.com/file2.txt', job=self.job)
        self.file_model_dao.create_file_model(url='http://example.com/file3.txt', job=self.job)

        # Retrieve all file models
        file_models = self.file_model_dao.get_all_file_models()

        # Assert that the correct number of file models is retrieved
        self.assertEqual(len(file_models), 3)

    def test_update_file_model_status(self):
        # Create a new file model and update its status
        new_file_model = self.file_model_dao.create_file_model(
            job=self.job,
            url='http://example.com/file1.txt'
        )
        self.file_model_dao.update_file_model_status(new_file_model.id, 'Downloaded')

        # Retrieve the updated file model by its ID
        updated_file_model = self.file_model_dao.get_file_model_by_id(new_file_model.id)

        # Assert that the status is updated
        self.assertEqual(updated_file_model.status, 'Downloaded')

    def test_delete_file_model(self):
        # Create a new file model and delete it
        new_file_model = self.file_model_dao.create_file_model(
            job=self.job,
            url='http://example.com/file1.txt'
        )
        self.file_model_dao.delete_file_model(new_file_model.id)

        # Try to retrieve the deleted file model by its ID
        deleted_file_model = self.file_model_dao.get_file_model_by_id(new_file_model.id)

        # Assert that the deleted file model is not found
        self.assertIsNone(deleted_file_model)

    def test_when_file_model_deleted_file_events_are_also_deleted(self):
        # Create a new file model and add a file event
        new_file_model = self.file_model_dao.create_file_model(
            job=self.job,
            url='http://example.com/file1.txt'
        )
        id = new_file_model.id
        self.file_event_dao.add_file_event(new_file_model, 'Test event')
        file_events_before_delete = self.file_event_dao.get_file_events_by_file_id(id)
        self.assertEqual(len(file_events_before_delete), 1)

        # Delete the file model
        self.file_model_dao.delete_file_model(new_file_model.id)

        # Retrieve all file events
        file_events = self.file_event_dao.get_file_events_by_file_id(id)

        # Assert that the file event is also deleted
        self.assertEqual(len(file_events), 0)

    def test_delete_all_file_models(self):
        # Create multiple file models
        self.file_model_dao.create_file_model(url='http://example.com/file1.txt', job=self.job)
        self.file_model_dao.create_file_model(url='http://example.com/file2.txt', job=self.job)
        self.file_model_dao.create_file_model(url='http://example.com/file3.txt', job=self.job)

        # Delete all file models
        self.file_model_dao.delete_all_file_models()

        # Retrieve all file models after deletion
        file_models = self.file_model_dao.get_all_file_models()

        # Assert that there are no file models left
        self.assertEqual(len(file_models), 0)


if __name__ == '__main__':
    unittest.main()
