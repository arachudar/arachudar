"""
tests/helpers/virtual_clock.py - Virtual Clock & Rate Limiting Simulation Helper.
Enables instant deterministic testing of TokenBucketRateLimiter pacing without wall-clock sleep.
"""

from typing import List


class VirtualClock:
    """
    Controllable virtual clock simulating time.monotonic and time.sleep.
    Tracks sleep call durations to verify rate limiting pacing without real-time delay.
    """

    def __init__(self, start_time: float = 1000.0):
        self.current_time = start_time
        self.sleep_history: List[float] = []

    def monotonic(self) -> float:
        """Returns the current simulated monotonic timestamp."""
        return self.current_time

    def sleep(self, seconds: float):
        """Simulates time.sleep by advancing the virtual clock and recording duration."""
        if seconds > 0:
            self.sleep_history.append(seconds)
            self.current_time += seconds

    def advance(self, seconds: float):
        """Manually advances the clock without recording a sleep event."""
        self.current_time += seconds

    def reset(self, start_time: float = 1000.0):
        """Resets the clock and clears history."""
        self.current_time = start_time
        self.sleep_history.clear()

    @property
    def total_slept(self) -> float:
        """Total accumulated sleep duration in simulated seconds."""
        return sum(self.sleep_history)


def verify_rate_limit_timings(
    sleep_calls: List[float],
    expected_delay: float = 2.0,
    tolerance: float = 0.5
):
    """
    Asserts that rate limiter enforced appropriate pacing when burst was exhausted.
    
    Args:
        sleep_calls: List of sleep durations captured during the run.
        expected_delay: Expected minimum sleep per request once burst is depleted.
        tolerance: Allowed deviation below expected_delay.
    """
    assert len(sleep_calls) > 0, "No rate limiting sleep calls recorded!"
    for delay in sleep_calls:
        assert delay >= (expected_delay - tolerance), (
            f"Rate limiter sleep {delay:.3f}s was below safety threshold ({expected_delay - tolerance:.3f}s)"
        )
