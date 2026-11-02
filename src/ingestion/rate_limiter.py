import asyncio
import time
from typing import List


class LeakyBucketRateLimiter:
    """Asynchronous rate limiter adhering strictly to API call caps (e.g. max 28 req/60s)."""

    def __init__(self, max_requests: int = 28, period_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.period = period_seconds
        self.timestamps: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquires a token, asynchronously sleeping if rate limit is reached."""
        async with self._lock:
            now = time.monotonic()
            # Retain only timestamps within the rolling window
            self.timestamps = [t for t in self.timestamps if now - t < self.period]

            if len(self.timestamps) >= self.max_requests:
                oldest = self.timestamps[0]
                sleep_duration = self.period - (now - oldest) + 0.05
                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)
                    now = time.monotonic()
                    self.timestamps = [t for t in self.timestamps if now - t < self.period]

            self.timestamps.append(now)
