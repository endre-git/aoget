from aoget.model.dao.file_event_dao import FileEventDAO
        self.file_event_dao = FileEventDAO(self.session)
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
