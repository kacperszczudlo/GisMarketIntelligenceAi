import asyncio
import time
import pytest
from src.ingestion.rate_limiter import LeakyBucketRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_throttles_burst():
    """Verify that requests exceeding max_requests within the period are throttled."""
    limiter = LeakyBucketRateLimiter(max_requests=3, period_seconds=1.0)
    start = time.monotonic()
    
    # 4 requests with limit of 3 per 1.0 second
    for _ in range(4):
        await limiter.acquire()
        
    duration = time.monotonic() - start
    # 4th request must be delayed until period elapses
    assert duration >= 0.95


@pytest.mark.asyncio
async def test_rate_limiter_concurrent_burst():
    """Verify thread-safe/task-safe rate limiting under concurrent calls."""
    limiter = LeakyBucketRateLimiter(max_requests=5, period_seconds=0.5)
    start = time.monotonic()

    tasks = [limiter.acquire() for _ in range(6)]
    await asyncio.gather(*tasks)

    duration = time.monotonic() - start
    assert duration >= 0.45
