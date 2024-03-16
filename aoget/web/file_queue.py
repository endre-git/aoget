import queue
from typing import List
from model.dto.file_model_dto import FileModelDTO

POISON_PILL = FileModelDTO(job_name="_poison_pill_", name="_poison_pill_", priority=0)


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
        self.REMOVED = FileModelDTO(job_name="_removed_", name="_removed_", priority=0)

    def is_poison_pill(entry: FileModelDTO) -> bool:
        """Returns True if the tested entry is a poison pill, False otherwise."""
        return (
            entry is not None
            and entry.name is not None
            and entry.name == POISON_PILL.name
        )

    def poison_pill(self) -> None:
        """Put an entry to the queue which is by convention a poison pill."""
        self.put_file(POISON_PILL)

    def put_all(self, files: List[FileModelDTO]) -> None:
        """Put all files into the queue with the given priority.
        :param files:
            The files to put into the queue"""
        for file in files:
            self.put_file(file)

    def remove_all(self, files: List[FileModelDTO]) -> None:
        """Remove all files from the queue.
        :param files:
            The files to remove"""
        for file in files:
            self.remove_file(file)

    def put_file(self, file: FileModelDTO) -> None:
        """Put a file into the queue.
        :param file:
            The file to put into the queue"""
        # poison pill has a priority treatment
        if FileQueue.is_poison_pill(file):
            self.put([0, file])
        else:
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
        if file.name not in self.entry_finder:
            return
        entry = self.entry_finder.pop(file.name)
        entry[-1] = self.REMOVED

    def pop_file(self) -> FileModelDTO:
        """Pop a file from the queue.
        :return:
            The file"""
        _, file = self.get()
        while file is self.REMOVED:
            _, file = self.get()
        if file is not None and not FileQueue.is_poison_pill(file):
            del self.entry_finder[file.name]
        return file
