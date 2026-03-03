"""
Rate limiter to prevent API abuse.
"""

import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter per user."""

    def __init__(self, max_messages: int = 30, period_seconds: int = 60):
        self.max_messages = max_messages
        self.period_seconds = period_seconds
        self._user_timestamps: dict[int, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if a user is allowed to send a message.

        Returns:
            True if the user hasn't exceeded the rate limit.
        """
        now = time.time()
        cutoff = now - self.period_seconds

        # Clean old timestamps
        self._user_timestamps[user_id] = [
            ts for ts in self._user_timestamps[user_id] if ts > cutoff
        ]

        if len(self._user_timestamps[user_id]) >= self.max_messages:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False

        self._user_timestamps[user_id].append(now)
        return True

    def get_remaining(self, user_id: int) -> int:
        """Get remaining messages for a user in the current period."""
        now = time.time()
        cutoff = now - self.period_seconds

        self._user_timestamps[user_id] = [
            ts for ts in self._user_timestamps[user_id] if ts > cutoff
        ]

        return max(0, self.max_messages - len(self._user_timestamps[user_id]))

    def get_reset_time(self, user_id: int) -> float | None:
        """Get the time until the rate limit resets for a user."""
        if not self._user_timestamps[user_id]:
            return None

        oldest = min(self._user_timestamps[user_id])
        reset_time = oldest + self.period_seconds - time.time()
        return max(0, reset_time)
