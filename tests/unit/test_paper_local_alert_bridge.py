"""Tests for local alert bridge."""
from __future__ import annotations

import pytest

from core.paper_trading.local_alert_bridge import Alert, AlertLevel, LocalAlertBridge


class TestLocalAlertBridge:
    def test_push_and_count(self):
        bridge = LocalAlertBridge()
        assert bridge.count == 0
        bridge.info("test", "hello")
        assert bridge.count == 1

    def test_info_warning_critical(self):
        bridge = LocalAlertBridge()
        bridge.info("cat", "msg1")
        bridge.warning("cat", "msg2")
        bridge.critical("cat", "msg3")
        assert bridge.count == 3
        alerts = bridge.peek()
        assert alerts[0].level == AlertLevel.INFO
        assert alerts[1].level == AlertLevel.WARNING
        assert alerts[2].level == AlertLevel.CRITICAL

    def test_drain_clears(self):
        bridge = LocalAlertBridge()
        bridge.info("x", "a")
        bridge.info("x", "b")
        drained = bridge.drain()
        assert len(drained) == 2
        assert bridge.count == 0

    def test_peek_does_not_clear(self):
        bridge = LocalAlertBridge()
        bridge.info("x", "a")
        peeked = bridge.peek()
        assert len(peeked) == 1
        assert bridge.count == 1

    def test_has_critical(self):
        bridge = LocalAlertBridge()
        assert not bridge.has_critical()
        bridge.info("x", "a")
        assert not bridge.has_critical()
        bridge.critical("x", "b")
        assert bridge.has_critical()

    def test_alert_source(self):
        bridge = LocalAlertBridge()
        bridge.info("cat", "msg", source="replay_engine")
        alert = bridge.peek()[0]
        assert alert.source == "replay_engine"

    def test_alert_frozen(self):
        alert = Alert(level=AlertLevel.INFO, category="c", message="m")
        with pytest.raises(AttributeError):
            alert.level = AlertLevel.CRITICAL  # type: ignore

    def test_multiple_categories(self):
        bridge = LocalAlertBridge()
        bridge.info("risk", "risk msg")
        bridge.warning("exit", "exit msg")
        bridge.critical("order", "order msg")
        alerts = bridge.drain()
        categories = {a.category for a in alerts}
        assert categories == {"risk", "exit", "order"}
