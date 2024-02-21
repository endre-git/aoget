from threading import RLock
from controller.app_cache import AppCache
from controller.downloads import Downloads
from controller.update_cycle import UpdateCycle
from controller.journal_daemon import JournalDaemon
from web.rate_limiter import RateLimiter


class AppStateHandlers:
    """ "Convenience class to bundle upp the app state handlers so that they can
    be passed around as a single object. Also helps to avoid circular imports."""

    def __init__(self, db_lock: RLock, main_window) -> None:
        """Create a new AppStateHandlers object."""
        self.db_lock = db_lock
        self.cache = AppCache()
        self.rate_limiter = RateLimiter()
        self.downloads = Downloads(self)
        self.update_cycle = UpdateCycle(self, main_window)
        self.journal_daemon = JournalDaemon(
            update_interval_seconds=1, journal_processor=self.update_cycle
        )
