import logging
from queue import Queue
from threading import Thread
from typing import Callable

logger = logging.getLogger(__name__)


class DbUpdateQueue:
    """A queue of commits to be processed by the database."""

    def __init__(self):
        self._queue = Queue()
        self._queue_thread = Thread(target=self._process_queue)
        self._queue_thread.start()
        self._msg_count = 0

    def _process_queue(self):
        """Process the queue."""
        while True:
            # increment the message count, log every 50th write
            self._msg_count += 1
            if self._msg_count % 100 == 0:
                logger.info(f"Processed {self._msg_count} DB updates.")
            commit = self._queue.get()
            commit()
            self._queue.task_done()

    def put(self, commit: Callable[[], None]) -> None:
        """Add a commit to the queue.
        :param commit:
            The commit to add"""
        self._queue.put(commit)

    def join(self) -> None:
        """Wait for all commits in the queue to be processed."""
        self._queue.join()
