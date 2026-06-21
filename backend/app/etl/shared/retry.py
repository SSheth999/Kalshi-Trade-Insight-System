import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from kalshi_python_async.exceptions import ApiException

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 5,
    base_delay: float = 1.0,
) -> T:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except ApiException as exc:
            if exc.status != 429 or attempt == max_attempts - 1:
                raise
            last_error = exc
            await asyncio.sleep(base_delay * (2**attempt))
    raise last_error  # unreachable
