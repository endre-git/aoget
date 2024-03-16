import unittest
from aoget.web.file_queue import FileQueue
from aoget.model.dto.file_model_dto import FileModelDTO


class TestFileQueue(unittest.TestCase):

    def test_remove_all(self):
        queue = FileQueue()
        file1 = FileModelDTO(name="testfile1", job_name="test_job", priority=2)
        file2 = FileModelDTO(name="testfile2", job_name="test_job", priority=2)
        file3 = FileModelDTO(name="testfile3", job_name="test_job", priority=2)
        queue.put_file(file1)
        queue.put_file(file2)
        queue.put_file(file3)
        queue.remove_all([file1, file2, file3])
        file4 = FileModelDTO(name="testfile4", job_name="test_job", priority=2)
        queue.put_file(file4)
        popped = queue.pop_file()
        assert popped.name == "testfile4"

    def test_cant_put_null(self):
        queue = FileQueue()
        with self.assertRaises(ValueError):
            queue.put_file(None)

    def test_poison_pill(self):
        queue = FileQueue()
        queue.poison_pill()
        popped = queue.pop_file()
        assert FileQueue.is_poison_pill(popped)


if __name__ == "__main__":
    unittest.main()
