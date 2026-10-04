"""Reconnect delays, pure: exponential with jitter, and a floor while the receiver is full."""

from collections.abc import Callable

JITTER = 0.25  # each delay varies by ±25 %, so restarts across clients don't line up


def reconnect_delay(attempt: int, initial_s: float, max_s: float, rand: Callable[[], float]) -> float:
    """Delay before reconnect attempt `attempt` (1, 2, …): initial · 2^(attempt−1), capped, jittered."""
    base = min(max_s, initial_s * 2 ** max(0, attempt - 1))
    return base * (1 - JITTER + 2 * JITTER * rand())


def busy_delay(attempt: int, initial_s: float, max_s: float, busy_retry_s: float,
               rand: Callable[[], float]) -> float:
    """While all free channels are taken: never sooner than busy_retry_s."""
    return max(busy_retry_s, reconnect_delay(attempt, initial_s, max_s, rand))
