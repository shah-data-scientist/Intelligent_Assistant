"""
FILE: retry.py
STATUS: Active
RESPONSIBILITY: Provides retry decorators and utilities for handling transient network failures with exponential backoff.

DEPENDENCIES (Who uses this file):
- src/data/api_client.py: Retries OpenAgenda API requests
- src/data/scraper.py: Retries web scraping requests
- src/utils/geo.py: Retries geocoding API calls
- src/evaluation/llm_backends.py: Retries LLM API calls

IMPORTS (What this file needs):
- functools: wraps decorator for preserving function metadata
- time: sleep for backoff delays
- logging: Log retry attempts
- typing: Type hints for generic retry decorator

LAST MAJOR UPDATE: 2026-01-30 (Initial implementation)
MAINTAINER: Infrastructure Team
"""

import functools
import logging
import time
from typing import Any, Callable, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    pass


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int, float], None] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 1.0)
        backoff_factor: Multiplier for delay after each attempt (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        exceptions: Tuple of exception types to catch and retry (default: all exceptions)
        on_retry: Optional callback function called on each retry with (exception, attempt, delay)

    Returns:
        Decorated function that retries on failure

    Example:
        ```python
        @retry_with_backoff(max_attempts=5, exceptions=(httpx.HTTPError,))
        def fetch_data():
            response = httpx.get("https://api.example.com/data")
            return response.json()
        ```
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            delay = initial_delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    attempt += 1

                    if attempt >= max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts. "
                            f"Last error: {type(e).__name__}: {str(e)}"
                        )
                        raise RetryExhaustedError(f"Failed after {max_attempts} attempts. Last error: {str(e)}") from e

                    # Calculate delay with exponential backoff
                    current_delay = min(delay, max_delay)

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}). "
                        f"Error: {type(e).__name__}: {str(e)}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )

                    # Call optional retry callback
                    if on_retry:
                        on_retry(e, attempt, current_delay)

                    time.sleep(current_delay)
                    delay *= backoff_factor

            # This should never be reached due to the raise in the loop
            raise RuntimeError("Unexpected retry logic failure")

        return wrapper

    return decorator


def retry_on_network_error(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Convenience decorator for retrying HTTP/network operations.

    Pre-configured to catch common network exceptions:
    - httpx.HTTPError
    - httpx.RequestError
    - httpx.TimeoutException
    - ConnectionError
    - TimeoutError

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 1.0)

    Returns:
        Decorated function that retries on network failures

    Example:
        ```python
        @retry_on_network_error(max_attempts=5)
        def fetch_events():
            return httpx.get("https://api.example.com/events").json()
        ```
    """
    try:
        import httpx

        network_exceptions = (
            httpx.HTTPError,
            httpx.RequestError,
            httpx.TimeoutException,
            ConnectionError,
            TimeoutError,
        )
    except ImportError:
        # If httpx not installed, fall back to basic exceptions
        network_exceptions = (ConnectionError, TimeoutError)

    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=2.0,
        max_delay=30.0,
        exceptions=network_exceptions,
    )


def retry_on_api_error(
    max_attempts: int = 3,
    initial_delay: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Convenience decorator for retrying LLM API operations.

    Pre-configured to catch common API exceptions:
    - Rate limit errors (429)
    - Server errors (500+)
    - Timeout errors

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 2.0)

    Returns:
        Decorated function that retries on API failures

    Example:
        ```python
        @retry_on_api_error(max_attempts=5, initial_delay=3.0)
        def call_llm(prompt: str):
            return mistral_client.chat(messages=[{"role": "user", "content": prompt}])
        ```
    """
    try:
        import httpx

        api_exceptions = (
            httpx.HTTPStatusError,  # Includes 429, 500, 503
            httpx.TimeoutException,
            ConnectionError,
            TimeoutError,
        )
    except ImportError:
        api_exceptions = (ConnectionError, TimeoutError)

    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=2.0,
        max_delay=60.0,
        exceptions=api_exceptions,
    )


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test 1: Retry on transient failure
    attempt_counter = {"count": 0}

    @retry_with_backoff(max_attempts=3, initial_delay=0.5)
    def flaky_function():
        attempt_counter["count"] += 1
        if attempt_counter["count"] < 3:
            raise ConnectionError("Simulated network failure")
        return "Success!"

    try:
        result = flaky_function()
        logger.info(f"Result: {result}")
    except RetryExhaustedError:
        logger.error("All retries exhausted")

    # Test 2: Retry exhaustion
    @retry_with_backoff(max_attempts=2, initial_delay=0.1)
    def always_fails():
        raise ValueError("Always fails")

    try:
        always_fails()
    except RetryExhaustedError as e:
        logger.info(f"Expected failure: {e}")
