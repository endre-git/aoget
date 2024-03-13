from threading import RLock
from controller.app_cache import AppCache
from controller.downloads import Downloads
from controller.update_cycle import UpdateCycle
from controller.journal_daemon import JournalDaemon
from web.rate_limiter import RateLimiter


class AppStateHandlers:
    """ "Convenience class to bundle up the app state handlers so that they can
    be passed around as a single object. Also helps to avoid circular imports."""

    def __init__(
        self, db_lock: RLock, main_window, start_journal_daemon: bool = True
    ) -> None:
        """Create a new AppStateHandlers object."""
        self.db_lock = db_lock
        self.main_window = main_window
        self.cache = AppCache()
        self.rate_limiter = RateLimiter()
        self.downloads = Downloads(self)
        self.update_cycle = UpdateCycle(self, main_window)
        self.journal_daemon = JournalDaemon(
            update_interval_seconds=1,
            journal_processor=self.update_cycle,
            start_daemon=start_journal_daemon,
        )
        self.job_locks = {}

    def job_lock(self, job_name: str) -> RLock:
        """Get the lock for the given job name."""
        if job_name not in self.job_locks:
            self.job_locks[job_name] = RLock()
        return self.job_locks[job_name]
