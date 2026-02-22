"""Lightweight in-process metrics collector.

Tracks counters and timing histograms without external dependencies.
Designed to be exported via the /health endpoint or a future /metrics endpoint.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class _Bucket:
    count: int = 0
    total: float = 0.0
    min_val: float = float("inf")
    max_val: float = 0.0

    def record(self, value: float) -> None:
        self.count += 1
        self.total += value
        if value < self.min_val:
            self.min_val = value
        if value > self.max_val:
            self.max_val = value

    def snapshot(self) -> dict:
        avg = (self.total / self.count) if self.count else 0.0
        return {
            "count": self.count,
            "total_ms": round(self.total, 2),
            "avg_ms": round(avg, 2),
            "min_ms": round(self.min_val, 2) if self.count else 0,
            "max_ms": round(self.max_val, 2) if self.count else 0,
        }


@dataclass
class MetricsCollector:
    """Thread-safe metrics collector with counters and timers."""

    _counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _timers: dict[str, _Bucket] = field(default_factory=lambda: defaultdict(_Bucket))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] += amount

    def record_time(self, name: str, duration_ms: float) -> None:
        with self._lock:
            self._timers[name].record(duration_ms)

    @contextmanager
    def timer(self, name: str) -> Generator[None, None, None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.record_time(name, elapsed_ms)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "timers": {k: v.snapshot() for k, v in self._timers.items()},
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timers.clear()


# Global singleton
metrics = MetricsCollector()
