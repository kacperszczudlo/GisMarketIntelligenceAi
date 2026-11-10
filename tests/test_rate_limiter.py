import asyncio
import time
import pytest
from pytest_mock import MockerFixture
from src.ingestion.rate_limiter import LeakyBucketRateLimiter

BURST_MAX_REQUESTS = 3
BURST_PERIOD_SECONDS = 0.25
CONCURRENT_MAX_REQUESTS = 4
CONCURRENT_PERIOD_SECONDS = 0.20


@pytest.mark.asyncio
async def test_should_allow_immediate_execution_when_under_rate_limit() -> None:
    # Arrange
    limiter = LeakyBucketRateLimiter(max_requests=BURST_MAX_REQUESTS, period_seconds=1.0)
    start = time.monotonic()

    # Act
    for _ in range(BURST_MAX_REQUESTS):
        await limiter.acquire()

    duration = time.monotonic() - start

    # Assert
    assert len(limiter.timestamps) == BURST_MAX_REQUESTS
    assert duration < 0.20


@pytest.mark.asyncio
async def test_should_throttle_burst_exceeding_max_requests_within_rolling_window() -> None:
    # Arrange
    limiter = LeakyBucketRateLimiter(
        max_requests=BURST_MAX_REQUESTS,
        period_seconds=BURST_PERIOD_SECONDS,
    )
    start = time.monotonic()

    # Act
    for _ in range(BURST_MAX_REQUESTS + 1):
        await limiter.acquire()

    duration = time.monotonic() - start

    # Assert
    assert duration >= BURST_PERIOD_SECONDS


@pytest.mark.asyncio
async def test_should_enforce_rate_limit_safely_across_concurrent_tasks() -> None:
    # Arrange
    limiter = LeakyBucketRateLimiter(
        max_requests=CONCURRENT_MAX_REQUESTS,
        period_seconds=CONCURRENT_PERIOD_SECONDS,
    )
    start = time.monotonic()

    # Act
    tasks = [limiter.acquire() for _ in range(CONCURRENT_MAX_REQUESTS + 1)]
    await asyncio.gather(*tasks)

    duration = time.monotonic() - start

    # Assert
    assert duration >= CONCURRENT_PERIOD_SECONDS


@pytest.mark.asyncio
async def test_should_prune_expired_timestamps_outside_rolling_window(
    mocker: MockerFixture,
) -> None:
    # Arrange
    limiter = LeakyBucketRateLimiter(max_requests=2, period_seconds=10.0)
    limiter.timestamps = [100.0, 101.0]
    mocker.patch("src.ingestion.rate_limiter.time.monotonic", return_value=115.0)
    mock_sleep = mocker.patch("src.ingestion.rate_limiter.asyncio.sleep", new_callable=mocker.AsyncMock)

    # Act
    await limiter.acquire()

    # Assert
    mock_sleep.assert_not_awaited()
    assert limiter.timestamps == [115.0]
