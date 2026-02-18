"""
Time-series smoothing utilities for solar/load curves.
Keeps complexity O(n) with configurable window size.
"""
from typing import List


def moving_average(values: List[float], window: int) -> List[float]:
    """
    Compute moving average. Edge handling: partial windows at boundaries.
    Time complexity: O(n * min(window, n)).
    """
    if not values or window < 1:
        return list(values)
    n = len(values)
    if window >= n:
        avg = sum(values) / n
        return [avg] * n
    result: List[float] = []
    for i in range(n):
        start = max(0, i - window + 1)
        end = i + 1
        result.append(sum(values[start:end]) / (end - start))
    return result


def clamp_soc(soc: float, min_pct: float = 0.0, max_pct: float = 100.0) -> float:
    """Clamp SoC to valid range."""
    return max(min_pct, min(max_pct, soc))
