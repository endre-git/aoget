import queue
from model.dto.file_model_dto import FileModelDTO


class FileQueue(queue.PriorityQueue):
    """A priority queue for files. Allows updating the priority of files
    already in the queue."""

    def __init__(self):
        """Create a new file queue."""
        super().__init__()
        self.entry_finder = {}  # Mapping from item to priority
        # this needs the be a FileModelDTO to keep elements sortable,
        # although sort order won't matter for the placeholder, since
        # it's always discarded
        self.REMOVED = FileModelDTO(job_name="_removed_", name="_removed_")

    def put_file(self, file: FileModelDTO) -> None:
        """Put a file into the queue with the given priority.
        :param file:
            The file to put into the queue
        :param priority:
            The priority of the file"""
        if file is None:
            entry = [0, None]
            self.put(entry)
            return

        if file.name in self.entry_finder:
            self.remove_file(file)
        entry = [file.priority, file]
        self.entry_finder[file.name] = entry
        self.put(entry)

    def remove_file(self, file: FileModelDTO) -> None:
        """Remove a file from the queue.
        :param file:
            The file to remove"""
        entry = self.entry_finder.pop(file.name)
        entry[-1] = self.REMOVED

    def pop_file(self) -> tuple[int, FileModelDTO]:
        """Pop a file from the queue.
        :return:
            The priority and file"""
        _, file = self.get()
        if file is not self.REMOVED:
            if file is not None:
                del self.entry_finder[file.name]
            return file
        else:
            return self.pop_file()[1]
