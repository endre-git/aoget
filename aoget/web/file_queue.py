import queue
from typing import List
from model.dto.file_model_dto import FileModelDTO


class FileQueue(queue.PriorityQueue):
    """A priority queue for files. Allows updating the priority of files
    already in the queue."""

    POISON_PILL = FileModelDTO(job_name="_poison_pill_", name="_poison_pill_", priority=0)

    def __init__(self):
        """Create a new file queue."""
        super().__init__()
        self.entry_finder = {}  # Mapping from item to priority
        # this needs the be a FileModelDTO to keep elements sortable,
        # although sort order won't matter for the placeholder, since
        # it's always discarded
        self.REMOVED = FileModelDTO(job_name="_removed_", name="_removed_", priority=0)

    def is_poison_pill(entry: FileModelDTO) -> bool:
        """Returns True if the tested entry is a poison pill, False otherwise."""
        return entry.name is not None and entry.name == FileQueue.POISON_PILL.name

    def poison_pill(self) -> None:
        """Put an entry to the queue which is by convention a poison pill."""
        self.put_file(FileQueue.POISON_PILL)

    def put_all(self, files: List[FileModelDTO]) -> None:
        """Put all files into the queue with the given priority.
        :param files:
            The files to put into the queue"""
        for file in files:
            self.put_file(file)

    def put_file(self, file: FileModelDTO) -> None:
        """Put a file into the queue.
        :param file:
            The file to put into the queue"""
        if file is None:
            raise ValueError(
                "Can't add None to this queue. Use .poison_pill() instead."
            )
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

    def pop_file(self) -> FileModelDTO:
        """Pop a file from the queue.
        :return:
            The priority and file"""
        _, file = self.get()
        if file is not self.REMOVED:
            if file is not None:
                del self.entry_finder[file.name]
            return file
        else:
            return self.pop_file()
