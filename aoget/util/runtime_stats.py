import time
from collections import defaultdict


class RuntimeStats:
    """Keep track of the runtime statistics of a class."""

    def __init__(self):
        """Create a new RuntimeStats object."""
        self.totals = defaultdict(int)
        self.calls = defaultdict(int)
        self.averages = defaultdict(int)
        self.epochs = defaultdict(int)

    def check_in(self, method: str):
        """Call at the start of timing of a method."""
        self.epochs[method] = time.time()

    def check_out(self, method: str):
        """Call at the end of timing of a method."""
        if self.epochs[method] == 0:
            raise ValueError(f'check_out() called before check_in() for method {method}')
        self.totals[method] += time.time() - self.epochs[method]
        self.calls[method] += 1
        self.averages[method] = self.totals[method] / self.calls[method]

    def __str__(self) -> str:
        """Return a string representation of the runtime statistics."""
        return f"RuntimeStats(totals={self.totals}, calls={self.calls}, averages={self.averages})"

    def get_totals(self, limit: int = -1) -> str:
        """Returns the totals in reverse order."""
        totals = sorted(self.totals.items(), key=lambda item: item[1], reverse=True)
        if (limit > 0):
            return totals[:limit]
        else:
            return totals

    def get_averages(self, limit: int = -1) -> str:
        """Returns the averages in reverse order."""
        averages = sorted(self.averages.items(), key=lambda item: item[1], reverse=True)
        if (limit > 0):
            return averages[:limit]
        else:
            return averages

    def get_calls(self, limit: int = -1) -> str:
        """Returns the calls in reverse order."""
        calls = sorted(self.calls.items(), key=lambda item: item[1], reverse=True)
        if (limit > 0):
            return calls[:limit]
        else:
            return calls
