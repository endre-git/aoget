import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from aoget.model.file_event import FileEvent
from aoget.model.dao.file_event_dao import FileEventDAO
from aoget.model.dao.file_model_dao import FileModelDAO
from aoget.model.dao.job_dao import JobDAO
from aoget.model.file_model import FileModel
from aoget.model.job import Job


class TestFileEventDAO(unittest.TestCase):
    def setUp(self):

        # Create an SQLite in-memory database for testing
        self.engine = create_engine('sqlite:///:memory:')
        self.session = Session(self.engine)

        # Create the tables in the database
        FileEvent.metadata.create_all(self.engine)

        # Create an instance of FileEventDAO with the testing session
        self.file_event_dao = FileEventDAO(self.session)

        # We need to create a job and a file for the file events to be associated with.
        self.file_model_dao = FileModelDAO(self.session)
        self.job_dao = JobDAO(self.session)

        self.test_job = Job(name='Test Job', page_url='http://example.com', target_folder='/tmp')
        self.test_file_model = FileModel(job=self.test_job, url='http://example.com/file1.txt')
        self.job_dao.add_job(self.test_job)
        self.file_model_dao.add_file_model(self.test_file_model)
        self.assertEqual(1, self.test_file_model.id)

    def tearDown(self):
        # Close the session and dispose of the engine after each test
        self.session.close()
        self.engine.dispose()

    def test_create_file_event(self):
        # Create a new file event using create_file_event method
        new_file_event = self.file_event_dao.create_file_event(event='Downloaded',
                                                               file_model=self.test_file_model)

        # Retrieve the file event by its ID
        retrieved_file_event = self.file_event_dao.get_file_event_by_id(new_file_event.id)

        # Assert that the retrieved file event matches the created file event
        self.assertEqual(retrieved_file_event.event, 'Downloaded')

    def test_add_file_event(self):
        # Create a new file event
        new_file_event = FileEvent(event='Downloaded', file=self.test_file_model)

        # Add the file event using add_file_event method
        self.file_event_dao.add_file_event(new_file_event)

        # Retrieve the file event by its ID
        retrieved_file_event = self.file_event_dao.get_file_event_by_id(new_file_event.id)

        # Assert that the retrieved file event matches the added file event
        self.assertEqual(retrieved_file_event.event, 'Downloaded')

    def test_get_file_events_by_file_id(self):
        # Create multiple file events for a file
        self.file_event_dao.create_file_event(event='Downloaded', file_model=self.test_file_model)
        self.file_event_dao.create_file_event(event='Deleted', file_model=self.test_file_model)

        # Retrieve all file events for the file
        file_events = self.file_event_dao.get_file_events_by_file_id(file_id=1)

        # Assert that the correct number of file events is retrieved
        self.assertEqual(len(file_events), 3)  # 1 added by default, 2 created above

    def test_delete_file_event(self):
        # Create a new file event and delete it
        new_file_event = self.file_event_dao.create_file_event(event='Downloaded',
                                                               file_model=self.test_file_model)
        self.file_event_dao.delete_file_event(event_id=new_file_event.id)

        # Try to retrieve the deleted file event by its ID
        deleted_file_event = self.file_event_dao.get_file_event_by_id(event_id=new_file_event.id)

        # Assert that the deleted file event is not found
        self.assertIsNone(deleted_file_event)

    def test_delete_file_events_by_file_id(self):
        # Create multiple file events for a file
        self.file_event_dao.create_file_event(event='Downloaded', file_model=self.test_file_model)
        self.file_event_dao.create_file_event(event='Deleted', file_model=self.test_file_model)

        # Delete all file events for the file
        self.file_event_dao.delete_file_events_by_file_id(file_id=1)

        # Retrieve all file events for the file after deletion
        file_events = self.file_event_dao.get_file_events_by_file_id(file_id=1)

        # Assert that there are no file events left for the file
        self.assertEqual(len(file_events), 0)


if __name__ == '__main__':
    unittest.main()
