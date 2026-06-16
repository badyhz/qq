"""Tests for review queue module."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from core.paper_trading.review_queue import (
    OperatorStatus, ReviewCandidate,
    create_candidate, append_candidate, read_queue, read_pending,
    update_status, mark_watchlist, mark_rejected, mark_paper_approved,
    expire_old, queue_summary,
)


def _candidate(**kwargs):
    defaults = dict(
        symbol="BTCUSDT", strategy_name="macd_rebound", side="BUY",
        entry_price=50000.0, stop_loss=49000.0, take_profit=52000.0,
        score=62.0, rating="B", risk_summary="normal risk",
        source_run_id="test_run_001",
    )
    defaults.update(kwargs)
    return create_candidate(**defaults)


def _tmp_path():
    f = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    f.close()
    return f.name


class TestCreateCandidate:
    def test_basic_fields(self):
        c = _candidate()
        assert c.symbol == "BTCUSDT"
        assert c.operator_status == "PENDING_REVIEW"
        assert c.review_id
        assert c.timestamp.endswith("Z")
        assert "NO_REAL_ORDER" in c.safety_flags
        assert "PAPER_ONLY" in c.safety_flags
        assert "HUMAN_REVIEW_REQUIRED" in c.safety_flags

    def test_custom_fields(self):
        c = _candidate(symbol="ETHUSDT", score=80, rating="A")
        assert c.symbol == "ETHUSDT"
        assert c.score == 80
        assert c.rating == "A"


class TestAppendAndRead:
    def test_append_and_read(self):
        path = _tmp_path()
        try:
            c1 = _candidate(symbol="BTCUSDT")
            c2 = _candidate(symbol="ETHUSDT")
            append_candidate(c1, path)
            append_candidate(c2, path)
            entries = read_queue(path)
            assert len(entries) == 2
            assert entries[0].symbol == "BTCUSDT"
            assert entries[1].symbol == "ETHUSDT"
        finally:
            os.unlink(path)

    def test_read_empty(self):
        assert read_queue("/tmp/nonexistent_review_queue_empty.jsonl") == []

    def test_read_nonexistent(self):
        assert read_queue("/tmp/nonexistent_queue.jsonl") == []

    def test_read_by_status(self):
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            mark_watchlist(c.review_id, "interesting", path)
            pending = read_queue(path, "PENDING_REVIEW")
            watchlist = read_queue(path, "WATCHLIST")
            assert len(pending) == 0
            assert len(watchlist) == 1
        finally:
            os.unlink(path)

    def test_skips_corrupted_lines(self):
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            with open(path, "a") as f:
                f.write("not json\n")
                f.write("\n")
            entries = read_queue(path)
            assert len(entries) == 1
        finally:
            os.unlink(path)


class TestReadPending:
    def test_only_pending(self):
        path = _tmp_path()
        try:
            c1 = _candidate(symbol="BTCUSDT")
            c2 = _candidate(symbol="ETHUSDT")
            append_candidate(c1, path)
            append_candidate(c2, path)
            mark_watchlist(c1.review_id, "", path)
            pending = read_pending(path)
            assert len(pending) == 1
            assert pending[0].symbol == "ETHUSDT"
        finally:
            os.unlink(path)


class TestUpdateStatus:
    def test_mark_watchlist(self):
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            assert mark_watchlist(c.review_id, "keep watching", path)
            entries = read_queue(path)
            assert entries[0].operator_status == "WATCHLIST"
            assert entries[0].decision_reason == "keep watching"
        finally:
            os.unlink(path)

    def test_mark_rejected(self):
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            assert mark_rejected(c.review_id, "too risky", path)
            entries = read_queue(path)
            assert entries[0].operator_status == "REJECTED"
        finally:
            os.unlink(path)

    def test_mark_paper_approved(self):
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            assert mark_paper_approved(c.review_id, "looks good", path)
            entries = read_queue(path)
            assert entries[0].operator_status == "PAPER_APPROVED"
            # Paper approved does NOT create real orders
            assert "NO_REAL_ORDER" in entries[0].safety_flags
        finally:
            os.unlink(path)

    def test_invalid_status_rejected(self):
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            with pytest.raises(ValueError, match="Invalid status"):
                update_status(c.review_id, "INVALID_STATUS", path=path)
        finally:
            os.unlink(path)

    def test_not_found(self):
        path = _tmp_path()
        try:
            append_candidate(_candidate(), path)
            assert not mark_watchlist("nonexistent_id", "", path)
        finally:
            os.unlink(path)


class TestExpireOld:
    def test_expires_old(self):
        path = _tmp_path()
        try:
            # Create candidate with old timestamp
            c = _candidate()
            data = {
                **c.__dict__,
                "timestamp": "2020-01-01T00:00:00Z",
            }
            with open(path, "w") as f:
                f.write(json.dumps(data) + "\n")
            expired = expire_old(path, max_age_hours=24)
            assert expired == 1
            entries = read_queue(path)
            assert entries[0].operator_status == "EXPIRED"
        finally:
            os.unlink(path)

    def test_does_not_expire_recent(self):
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            expired = expire_old(path, max_age_hours=24)
            assert expired == 0
        finally:
            os.unlink(path)

    def test_does_not_expire_non_pending(self):
        path = _tmp_path()
        try:
            c = _candidate()
            data = {
                **c.__dict__,
                "timestamp": "2020-01-01T00:00:00Z",
                "operator_status": "WATCHLIST",
            }
            with open(path, "w") as f:
                f.write(json.dumps(data) + "\n")
            expired = expire_old(path, max_age_hours=24)
            assert expired == 0
        finally:
            os.unlink(path)


class TestQueueSummary:
    def test_summary(self):
        path = _tmp_path()
        try:
            for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
                append_candidate(_candidate(symbol=sym), path)
            s = queue_summary(path)
            assert s["PENDING_REVIEW"] == 3
            assert s["total"] == 3
        finally:
            os.unlink(path)


class TestPaperApprovedNoOrder:
    def test_paper_approved_never_creates_order(self):
        """PAPER_APPROVED is purely a review status — no order side effects."""
        path = _tmp_path()
        try:
            c = _candidate()
            append_candidate(c, path)
            mark_paper_approved(c.review_id, "test approval", path)
            entries = read_queue(path)
            assert entries[0].operator_status == "PAPER_APPROVED"
            # Verify no order-related fields exist
            data = entries[0].__dict__
            assert "order_id" not in data
            assert "execution_id" not in data
            assert "NO_REAL_ORDER" in data["safety_flags"]
        finally:
            os.unlink(path)
