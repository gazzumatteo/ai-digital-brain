"""Tests for the metrics collector."""

from __future__ import annotations

import time

from digital_brain.metrics import MetricsCollector


class TestMetricsCollector:
    def test_inc_counter(self):
        m = MetricsCollector()
        m.inc("requests")
        m.inc("requests")
        m.inc("requests", 3)
        snap = m.snapshot()
        assert snap["counters"]["requests"] == 5

    def test_record_time(self):
        m = MetricsCollector()
        m.record_time("latency", 100.0)
        m.record_time("latency", 200.0)
        snap = m.snapshot()
        timer = snap["timers"]["latency"]
        assert timer["count"] == 2
        assert timer["min_ms"] == 100.0
        assert timer["max_ms"] == 200.0
        assert timer["avg_ms"] == 150.0

    def test_timer_context_manager(self):
        m = MetricsCollector()
        with m.timer("operation"):
            time.sleep(0.01)
        snap = m.snapshot()
        assert snap["timers"]["operation"]["count"] == 1
        assert snap["timers"]["operation"]["avg_ms"] >= 5  # at least ~10ms

    def test_snapshot_empty(self):
        m = MetricsCollector()
        snap = m.snapshot()
        assert snap == {"counters": {}, "timers": {}}

    def test_reset(self):
        m = MetricsCollector()
        m.inc("a")
        m.record_time("b", 10.0)
        m.reset()
        snap = m.snapshot()
        assert snap == {"counters": {}, "timers": {}}

    def test_timer_records_on_exception(self):
        m = MetricsCollector()
        try:
            with m.timer("failing"):
                raise ValueError("boom")
        except ValueError:
            pass
        snap = m.snapshot()
        assert snap["timers"]["failing"]["count"] == 1
