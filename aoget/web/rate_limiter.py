class RateLimiter:
    """Rate limiter of download bandwidth."""

    def __init__(self, time_window_seconds: int = 1):
        """Rate limiter of download bandwidth.
        :param time_window: Time window in seconds in which the limiter calculatiosn are donw.
        """
        self.time_window_seconds = time_window_seconds
        self.rate_limit_bps = 0

    def set_global_rate_limit(self, rate_limit_bps: int):
        """Set the global rate limit in bytes per second."""
        self.rate_limit_bps = rate_limit_bps

    def get_per_thread_limit(self, download_thread_count: int) -> int:
        if self.rate_limit_bps == 0:
            return 0
        return self.rate_limit_bps / download_thread_count
