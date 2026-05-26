"""Unit tests for SingleCallRecorder."""

import time
import hashlib

import pytest

from core.single_call_recorder import SingleCallRecorder


@pytest.fixture
def rec():
    return SingleCallRecorder()


class TestStartRecord:
    def test_returns_record_id(self, rec):
        rid = rec.start_record(
            adapter_id="binance",
            request_id="req-001",
            capability_used="market_data",
            approval_token="secret-token-123",
            budget_before_usd=100.0,
        )
        assert isinstance(rid, str)
        assert len(rid) > 0

    def test_record_stored(self, rec):
        rid = rec.start_record(
            adapter_id="binance",
            request_id="req-001",
            capability_used="market_data",
            approval_token="tok",
            budget_before_usd=50.0,
        )
        record = rec.get_record(rid)
        assert record is not None
        assert record.adapter_id == "binance"
        assert record.request_id == "req-001"


class TestEndRecord:
    def test_fills_fields(self, rec):
        rid = rec.start_record(
            adapter_id="binance",
            request_id="req-001",
            capability_used="trade",
            approval_token="tok",
            budget_before_usd=100.0,
        )
        time.sleep(0.01)
        rec.end_record(rid, "success", "order filled", 99.5)
        record = rec.get_record(rid)
        assert record is not None
        assert record.ended_at is not None
        assert record.response_status == "success"
        assert record.response_summary == "order filled"
        assert record.budget_after_usd == 99.5

    def test_unknown_record_raises(self, rec):
        with pytest.raises(KeyError):
            rec.end_record("nonexistent", "success", "ok", 0.0)


class TestDuration:
    def test_duration_computed(self, rec):
        rid = rec.start_record(
            adapter_id="binance",
            request_id="req-001",
            capability_used="trade",
            approval_token="tok",
            budget_before_usd=100.0,
        )
        time.sleep(0.05)
        rec.end_record(rid, "success", "done", 100.0)
        record = rec.get_record(rid)
        assert record.duration_ms is not None
        assert record.duration_ms >= 40  # at least 40ms
        assert record.duration_ms < 5000


class TestTokenHashing:
    def test_hash_differs_from_raw(self, rec):
        raw = "super-secret-api-key-12345"
        rid = rec.start_record(
            adapter_id="binance",
            request_id="req-001",
            capability_used="trade",
            approval_token=raw,
            budget_before_usd=100.0,
        )
        record = rec.get_record(rid)
        assert record.approval_token_hash != raw

    def test_hash_is_sha256_hex(self, rec):
        raw = "my-secret-token"
        rid = rec.start_record(
            adapter_id="binance",
            request_id="req-001",
            capability_used="trade",
            approval_token=raw,
            budget_before_usd=100.0,
        )
        record = rec.get_record(rid)
        expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert record.approval_token_hash == expected

    def test_different_tokens_different_hashes(self, rec):
        r1 = rec.start_record("a", "r1", "cap", "token-A", 0.0)
        r2 = rec.start_record("a", "r2", "cap", "token-B", 0.0)
        h1 = rec.get_record(r1).approval_token_hash
        h2 = rec.get_record(r2).approval_token_hash
        assert h1 != h2


class TestResponseSummaryTruncation:
    def test_short_summary_unchanged(self, rec):
        rid = rec.start_record("a", "r1", "cap", "tok", 0.0)
        short = "ok"
        rec.end_record(rid, "success", short, 0.0)
        assert rec.get_record(rid).response_summary == short

    def test_truncated_at_200(self, rec):
        rid = rec.start_record("a", "r1", "cap", "tok", 0.0)
        long_summary = "x" * 300
        rec.end_record(rid, "success", long_summary, 0.0)
        summary = rec.get_record(rid).response_summary
        assert len(summary) == 200

    def test_exactly_200_not_truncated(self, rec):
        rid = rec.start_record("a", "r1", "cap", "tok", 0.0)
        exact = "y" * 200
        rec.end_record(rid, "success", exact, 0.0)
        assert rec.get_record(rid).response_summary == exact


class TestGetRecord:
    def test_returns_none_for_unknown(self, rec):
        assert rec.get_record("no-such-id") is None


class TestListRecords:
    def test_returns_all(self, rec):
        r1 = rec.start_record("a", "r1", "cap", "tok", 0.0)
        r2 = rec.start_record("b", "r2", "cap", "tok", 0.0)
        r3 = rec.start_record("c", "r3", "cap", "tok", 0.0)
        records = rec.list_records()
        ids = {r.record_id for r in records}
        assert ids == {r1, r2, r3}

    def test_empty_list(self, rec):
        assert rec.list_records() == []


class TestSummary:
    def test_empty_summary(self, rec):
        s = rec.summary()
        assert s["total_calls"] == 0
        assert s["by_adapter"] == {}
        assert s["by_status"] == {}

    def test_summary_counts(self, rec):
        rec.start_record("binance", "r1", "cap", "tok", 0.0)
        rec.start_record("binance", "r2", "cap", "tok", 0.0)
        rec.start_record("okx", "r3", "cap", "tok", 0.0)
        s = rec.summary()
        assert s["total_calls"] == 3
        assert s["by_adapter"]["binance"] == 2
        assert s["by_adapter"]["okx"] == 1

    def test_summary_by_status(self, rec):
        r1 = rec.start_record("a", "r1", "cap", "tok", 0.0)
        r2 = rec.start_record("a", "r2", "cap", "tok", 0.0)
        r3 = rec.start_record("a", "r3", "cap", "tok", 0.0)
        rec.end_record(r1, "success", "ok", 0.0)
        rec.end_record(r2, "error", "fail", 0.0)
        # r3 still open — no status
        s = rec.summary()
        assert s["by_status"]["success"] == 1
        assert s["by_status"]["error"] == 1


class TestBudgetTracking:
    def test_budget_before_and_after(self, rec):
        rid = rec.start_record("a", "r1", "cap", "tok", 100.0)
        rec.end_record(rid, "success", "ok", 98.5)
        record = rec.get_record(rid)
        assert record.budget_before_usd == 100.0
        assert record.budget_after_usd == 98.5

    def test_budget_after_none_before_end(self, rec):
        rid = rec.start_record("a", "r1", "cap", "tok", 50.0)
        record = rec.get_record(rid)
        assert record.budget_after_usd is None


class TestMultipleRecords:
    def test_multiple_records_tracked_independently(self, rec):
        r1 = rec.start_record("a", "r1", "cap1", "tok1", 10.0)
        r2 = rec.start_record("b", "r2", "cap2", "tok2", 20.0)
        rec.end_record(r1, "success", "done", 9.0)
        # r2 still open
        rec1 = rec.get_record(r1)
        rec2 = rec.get_record(r2)
        assert rec1.response_status == "success"
        assert rec1.budget_after_usd == 9.0
        assert rec2.response_status is None
        assert rec2.budget_after_usd is None
        assert rec1.capability_used == "cap1"
        assert rec2.capability_used == "cap2"
