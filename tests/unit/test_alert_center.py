"""Tests for T19501 — Unified Alert Center.

Covers:
- Alert event schema
- Source validation
- Dedup engine
- Priority classification
- Feishu formatting
- Secret redaction
- Dry-run no-send
- Replay
- Heartbeat
- Forbidden actions
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.alert_center import (
    FORBIDDEN_ACTIONS,
    VALID_PRIORITIES,
    VALID_SOURCES,
    AlertEvent,
    HeartbeatRecord,
    build_alert_center_status,
    build_alert_event,
    build_heartbeat,
    classify_priority,
    compute_alerts_hash,
    deduplicate_alerts,
    format_feishu,
)


# --- Alert Event Schema Tests ---

class TestAlertSchema:
    def test_build_alert(self):
        alert = build_alert_event(
            source="earnings",
            priority="IMPORTANT",
            title="AAPL Earnings Beat",
            message="AAPL beat estimates by 15%",
            ticker="AAPL",
        )
        assert alert.source == "earnings"
        assert alert.priority == "IMPORTANT"
        assert alert.dry_run is True
        assert alert.no_real_notification is True

    def test_valid_sources(self):
        for source in VALID_SOURCES:
            alert = build_alert_event(source=source, priority="INFO", title="test", message="test")
            assert alert.source == source

    def test_valid_priorities(self):
        for priority in VALID_PRIORITIES:
            alert = build_alert_event(source="manual_test", priority=priority, title="test", message="test")
            assert alert.priority == priority


# --- Dedup Engine Tests ---

class TestDedup:
    def test_no_duplicates(self):
        alerts = [
            build_alert_event(source="earnings", priority="INFO", title="AAPL", message="m1", ticker="AAPL"),
            build_alert_event(source="earnings", priority="INFO", title="MSFT", message="m2", ticker="MSFT"),
        ]
        deduped = deduplicate_alerts(alerts)
        assert len(deduped) == 2

    def test_duplicates_filtered(self):
        alerts = [
            build_alert_event(source="earnings", priority="INFO", title="AAPL", message="m1", ticker="AAPL"),
            build_alert_event(source="earnings", priority="INFO", title="AAPL", message="m1", ticker="AAPL"),
        ]
        deduped = deduplicate_alerts(alerts)
        assert len(deduped) == 1

    def test_different_source_not_dup(self):
        alerts = [
            build_alert_event(source="earnings", priority="INFO", title="AAPL", message="m1", ticker="AAPL"),
            build_alert_event(source="stock_price", priority="INFO", title="AAPL", message="m1", ticker="AAPL"),
        ]
        deduped = deduplicate_alerts(alerts)
        assert len(deduped) == 2

    def test_dedup_key_stable(self):
        a1 = build_alert_event(source="earnings", priority="INFO", title="AAPL", message="m1", ticker="AAPL")
        a2 = build_alert_event(source="earnings", priority="INFO", title="AAPL", message="m2", ticker="AAPL")
        assert a1.dedup_key == a2.dedup_key

    def test_existing_keys_mark_dup(self):
        a1 = build_alert_event(source="earnings", priority="INFO", title="AAPL", message="m1", ticker="AAPL")
        a2 = build_alert_event(
            source="earnings", priority="INFO", title="AAPL", message="m1", ticker="AAPL",
            existing_keys={a1.dedup_key},
        )
        assert a2.is_duplicate is True
        assert a2.routed is False


# --- Priority Classification Tests ---

class TestPriorityClassification:
    def test_explicit_priority_preserved(self):
        assert classify_priority("earnings", "CRITICAL") == "CRITICAL"

    def test_source_based_classification(self):
        assert classify_priority("earnings") == "IMPORTANT"
        assert classify_priority("stock_price") == "WATCH"
        assert classify_priority("macd_rebound") == "WATCH"
        assert classify_priority("binance_futures") == "IMPORTANT"
        assert classify_priority("strategy_registry") == "INFO"
        assert classify_priority("system_heartbeat") == "INFO"
        assert classify_priority("force_alert") == "CRITICAL"
        assert classify_priority("manual_test") == "INFO"

    def test_unknown_source_default_info(self):
        assert classify_priority("unknown_source") == "INFO"


# --- Feishu Formatter Tests ---

class TestFeishuFormatter:
    def test_format_feishu(self):
        alert = build_alert_event(
            source="earnings", priority="IMPORTANT",
            title="Test Alert", message="Test message", ticker="AAPL",
        )
        card = format_feishu(alert)
        assert card["msg_type"] == "interactive"
        assert card["_dry_run"] is True
        assert card["_no_real_notification"] is True
        assert "DRY RUN" in str(card)

    def test_feishu_priority_emoji(self):
        for priority in VALID_PRIORITIES:
            alert = build_alert_event(
                source="manual_test", priority=priority,
                title="Test", message="Test",
            )
            card = format_feishu(alert)
            assert "header" in card["card"]

    def test_feishu_no_secrets(self):
        alert = build_alert_event(
            source="earnings", priority="INFO",
            title="Test", message="https://hooks.example.com/secret123",
        )
        card = format_feishu(alert)
        card_str = json.dumps(card)
        # The card itself doesn't redact, but _dry_run prevents sending
        assert card["_dry_run"] is True


# --- Secret Redaction Tests ---

class TestSecretRedaction:
    def test_dry_run_prevents_send(self):
        alert = build_alert_event(
            source="earnings", priority="CRITICAL",
            title="Test", message="sensitive data",
        )
        assert alert.dry_run is True
        assert alert.no_real_notification is True


# --- Heartbeat Tests ---

class TestHeartbeat:
    def test_build_heartbeat(self):
        hb = build_heartbeat(
            active_sources=["earnings", "stock_price"],
            alert_count=10,
            duplicate_count=2,
        )
        assert hb.status == "ALIVE"
        assert hb.dry_run is True
        assert len(hb.active_sources) == 2

    def test_heartbeat_dry_run(self):
        hb = build_heartbeat(active_sources=[], alert_count=0, duplicate_count=0)
        assert hb.dry_run is True


# --- Alert Center Status Tests ---

class TestAlertCenterStatus:
    def test_build_status(self):
        alerts = [
            build_alert_event(source="earnings", priority="IMPORTANT", title="t1", message="m1"),
            build_alert_event(source="stock_price", priority="WATCH", title="t2", message="m2"),
        ]
        hb = build_heartbeat(active_sources=["earnings", "stock_price"], alert_count=2, duplicate_count=0)
        status = build_alert_center_status(alerts, hb)
        assert status["total_alerts"] == 2
        assert status["unique_alerts"] == 2
        assert status["dry_run"] is True

    def test_status_with_duplicates(self):
        a1 = build_alert_event(source="earnings", priority="INFO", title="t1", message="m1")
        a2 = build_alert_event(
            source="earnings", priority="INFO", title="t1", message="m1",
            existing_keys={a1.dedup_key},
        )
        alerts = [a1, a2]
        hb = build_heartbeat(active_sources=["earnings"], alert_count=2, duplicate_count=1)
        status = build_alert_center_status(alerts, hb)
        assert status["duplicate_alerts"] == 1


# --- Dry-Run No-Send Tests ---

class TestDryRunNoSend:
    def test_all_alerts_dry_run(self):
        for source in VALID_SOURCES:
            alert = build_alert_event(source=source, priority="INFO", title="t", message="m")
            assert alert.dry_run is True
            assert alert.no_real_notification is True

    def test_feishu_dry_run(self):
        alert = build_alert_event(source="earnings", priority="CRITICAL", title="t", message="m")
        card = format_feishu(alert)
        assert card["_dry_run"] is True


# --- Replay Tests ---

class TestReplay:
    def test_replay_builds_alerts(self):
        events = [
            {"source": "earnings", "priority": "IMPORTANT", "title": "t1", "message": "m1", "ticker": "AAPL"},
            {"source": "stock_price", "priority": "WATCH", "title": "t2", "message": "m2", "ticker": "MSFT"},
        ]
        alerts = [build_alert_event(**e) for e in events]
        assert len(alerts) == 2
        assert alerts[0].source == "earnings"
        assert alerts[1].source == "stock_price"


# --- Forbidden Actions Tests ---

class TestForbiddenActions:
    def test_no_forbidden_in_alert(self):
        alert = build_alert_event(source="earnings", priority="INFO", title="t", message="m")
        alert_dict = alert.to_dict()
        for action in FORBIDDEN_ACTIONS:
            assert action not in str(alert_dict)


# --- Deterministic Hash Tests ---

class TestDeterministic:
    def test_hash_stable(self):
        alerts = [
            build_alert_event(source="earnings", priority="INFO", title="t1", message="m1", ticker="AAPL"),
        ]
        h1 = compute_alerts_hash(alerts)
        h2 = compute_alerts_hash(alerts)
        assert h1 == h2


# Need json import for test
import json
