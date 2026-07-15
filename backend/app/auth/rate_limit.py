import asyncio
import time
from collections import deque
from typing import final

from fastapi import HTTPException, Request, status

from app.core.config import settings


@final
class SlidingWindowRateLimiter:
    MAX_TRACKED_KEYS = 10_000

    def __init__(self, *, requests: int, window_seconds: int) -> None:
        self._requests = requests
        self._window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, *, now: float | None = None) -> None:
        current_time = time.monotonic() if now is None else now
        cutoff = current_time - self._window_seconds
        async with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                if len(self._attempts) >= self.MAX_TRACKED_KEYS:
                    del self._attempts[next(iter(self._attempts))]
                attempts = deque[float]()
                self._attempts[key] = attempts
            while attempts and attempts[0] <= cutoff:
                _ = attempts.popleft()
            if len(attempts) >= self._requests:
                retry_after = max(1, int(attempts[0] + self._window_seconds - current_time) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many authentication attempts",
                    headers={"Retry-After": str(retry_after)},
                )
            attempts.append(current_time)


auth_rate_limiter = SlidingWindowRateLimiter(
    requests=settings.auth_rate_limit_requests,
    window_seconds=settings.auth_rate_limit_window_seconds,
)


async def enforce_auth_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client is not None else "unknown"
    await auth_rate_limiter.check(f"{request.url.path}:{client_host}")
