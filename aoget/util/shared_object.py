import threading
import logging

logger = logging.getLogger(__name__)


class SharedObject:
    """A thread-safe shared object."""

    def __init__(self, data=None):
        self.data = data
        self.lock = threading.Lock()

    def set(self, new_data):
        with self.lock:
            self.data = new_data

    def get(self):
        with self.lock:
            return self.data
