"""
src/ai/rate_limiter.py - Thread-safe Token Bucket Rate Limiter for Arachudar AI Subsystem.
Enforces client-side rate limits (default 30 RPM = 0.5 req/s, capacity = 4 tokens)
with injectable clock and sleep functions for deterministic virtual clock testing.
"""

import threading
import time
from typing import Optional, Callable


class TokenBucketRateLimiter:
    """
    Thread-safe Token Bucket Rate Limiter.
    Allows bursts up to capacity, then smoothly paces requests at a sustained rate.
    """

    def __init__(
        self,
        rate_rpm: Optional[float] = None,
        rate_per_sec: Optional[float] = None,
        rate: Optional[float] = None,
        capacity: float = 4.0,
        time_func: Optional[Callable[[], float]] = None,
        sleep_func: Optional[Callable[[float], None]] = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            rate_rpm: Requests per minute (e.g. 30.0 -> 0.5 tokens/sec).
            rate_per_sec: Requests per second (e.g. 0.5 tokens/sec).
            rate: Direct rate in tokens per second.
            capacity: Maximum token burst capacity (default 4.0).
            time_func: Time function returning seconds (default time.monotonic).
            sleep_func: Sleep function accepting seconds (default time.sleep).
        """
        if rate_per_sec is not None:
            computed_rate = float(rate_per_sec)
        elif rate is not None:
            computed_rate = float(rate)
        elif rate_rpm is not None:
            computed_rate = float(rate_rpm) / 60.0
        else:
            computed_rate = 30.0 / 60.0  # Default 30 RPM = 0.5 tokens/sec

        if computed_rate <= 0:
            raise ValueError(f"Rate must be strictly positive, got {computed_rate}")
        if capacity <= 0:
            raise ValueError(f"Capacity must be strictly positive, got {capacity}")

        self.rate = computed_rate
        self.capacity = float(capacity)
        self._tokens = float(capacity)
        self.time_func = time_func if time_func is not None else time.monotonic
        self.sleep_func = sleep_func if sleep_func is not None else time.sleep
        self.last_update = self.time_func()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Internal helper to calculate and add refilled tokens since last_update."""
        now = self.time_func()
        elapsed = now - self.last_update
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self.last_update = now
        elif elapsed < 0:
            # Handle clock skew (backward jump) gracefully without reducing tokens
            self.last_update = now

    @property
    def tokens(self) -> float:
        """Returns the current number of available tokens after refilling."""
        with self._lock:
            self._refill()
            return self._tokens

    @tokens.setter
    def tokens(self, value: float) -> None:
        """Sets the current token count directly under lock."""
        with self._lock:
            self._tokens = float(value)

    def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire the requested number of tokens, blocking if not enough are available.

        Args:
            tokens: Number of tokens to acquire (default 1.0).

        Returns:
            The duration in seconds spent sleeping (0.0 if immediate).
        """
        if tokens < 0:
            raise ValueError(f"Requested tokens ({tokens}) cannot be negative")

        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return 0.0

            deficit = tokens - self._tokens
            wait_time = deficit / self.rate
            self.sleep_func(wait_time)
            self._tokens = 0.0
            self.last_update = self.time_func()
            return wait_time

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        Attempt to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire (default 1.0).

        Returns:
            True if tokens were acquired, False otherwise.
        """
        if tokens < 0:
            raise ValueError(f"Requested tokens ({tokens}) cannot be negative")

        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False
