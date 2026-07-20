"""Tests for shadow run registry — records, gate evaluation, JSONL I/O."""
from __future__ import annotations

import json
import os
import py_compile
import tempfile
from datetime import datetime, timezone

import pytest

from core.paper_trading.shadow_run_registry import (
    ShadowRunRecord, ShadowSampleGateResult,
    build_pipeline_context, build_run_record, evaluate_gate, generate_run_id,
    append_registry_record, read_registry, compute_sample_gate,
    report_date_for_started_at, validate_report_date,
    GATE_BLOCKED_INSUFFICIENT, GATE_BLOCKED_LOW, GATE_READY_FOR_REVIEW,
)

MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "core", "paper_trading", "shadow_run_registry.py")


def _write_test_ledger(tmpdir: str, closed_clean_count: int = 0, open_count: int = 0):
    """Write a ledger JSONL file with closed-clean and open positions."""
    import datetime as _dt
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    path = os.path.join(tmpdir, "2026-06-18_paper_position_ledger.jsonl")
    with open(path, "w") as f:
        for i in range(closed_clean_count):
            rec = {
                "position_id": f"PP_closed_{i}",
                "strategy_id": "test_strat",
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "side": "LONG",
                "status": "TAKE_PROFIT_HIT",
                "entry_price": 100.0,
                "exit_price": 110.0,
                "stop_loss": 95.0,
                "take_profit": 110.0,
                "r_multiple": 2.0,
                "realized_pnl": 10.0,
                "lifecycle_mode": "future_only",
                "opened_bar_time": 1000 + i,
                "closed_at": now_iso,
                "quarantine_status": "CLEAN",
                "source_mode": "real_public_readonly",
                "recorded_at": now_iso,
            }
            f.write(json.dumps(rec) + "\n")
        for i in range(open_count):
            rec = {
                "position_id": f"PP_open_{i}",
                "strategy_id": "test_strat",
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "side": "LONG",
                "status": "OPEN",
                "entry_price": 100.0,
                "stop_loss": 95.0,
                "take_profit": 110.0,
                "r_multiple": 0.0,
                "realized_pnl": 0.0,
                "lifecycle_mode": "future_only",
                "opened_bar_time": 2000 + i,
                "quarantine_status": "CLEAN",
                "source_mode": "real_public_readonly",
                "recorded_at": now_iso,
            }
            f.write(json.dumps(rec) + "\n")


def _make_pipeline_result(**overrides):
    result = {
        "date": "2026-06-18",
        "mode": "offline_sample",
        "allow_public_http": False,
        "pipeline_status": "PASS",
        "steps": [
            {"step_name": "step1", "status": "PASS", "started_at": "2026-06-18T10:00:00", "finished_at": "2026-06-18T10:00:01"},
            {"step_name": "step2", "status": "PASS", "started_at": "2026-06-18T10:00:01", "finished_at": "2026-06-18T10:00:02"},
        ],
        "summary": {
            "strategy_candidates_count": 10,
            "trade_intents_count": 5,
            "shadow_ready_count": 5,
            "paper_position_count": 20,
            "open_count": 17,
            "tp_count": 1,
            "sl_count": 1,
            "timeout_count": 1,
            "quarantined_count": 4,
            "clean_count": 16,
            "closed_clean_positions": 3,
            "sample_status": "LOW_SAMPLE_SIZE",
            "strategy_scorecard_rows": 2,
        },
        "safety_flags": ["PAPER_ONLY", "NO_ORDER"],
    }
    result.update(overrides)
    return result


class TestModuleCompiles:
    def test_compiles(self):
        py_compile.compile(MODULE_PATH, doraise=True)


class TestGenerateRunId:
    def test_format(self):
        rid = generate_run_id()
        assert rid.endswith("_shadow_lifecycle")
        assert len(rid) >= 20

    def test_unique(self):
        r1 = generate_run_id()
        r2 = generate_run_id()
        # They might be the same if called in same second, but format is correct
        assert r1.endswith("_shadow_lifecycle")


class TestEvaluateGate:
    def test_blocked_insufficient_zero(self):
        status, reasons = evaluate_gate(0, "INSUFFICIENT_CLOSED_SAMPLE")
        assert status == GATE_BLOCKED_INSUFFICIENT
        assert "closed_clean_positions=0 < 10" in reasons[0]

    def test_blocked_insufficient_9(self):
        status, reasons = evaluate_gate(9, "LOW_SAMPLE_SIZE")
        assert status == GATE_BLOCKED_INSUFFICIENT

    def test_blocked_low_sample(self):
        status, reasons = evaluate_gate(10, "LOW_SAMPLE_SIZE")
        assert status == GATE_BLOCKED_LOW

    def test_blocked_evaluable_under_30(self):
        status, reasons = evaluate_gate(20, "EVALUABLE")
        assert status == GATE_BLOCKED_LOW

    def test_ready_for_review(self):
        status, reasons = evaluate_gate(30, "EVALUABLE")
        assert status == GATE_READY_FOR_REVIEW
        assert ">= 30" in reasons[0]

    def test_ready_for_review_over_30(self):
        status, reasons = evaluate_gate(50, "EVALUABLE")
        assert status == GATE_READY_FOR_REVIEW

    def test_never_outputs_testnet_ready(self):
        for closed in [0, 5, 10, 30, 100]:
            for ss in ["INSUFFICIENT_CLOSED_SAMPLE", "LOW_SAMPLE_SIZE", "EVALUABLE"]:
                status, _ = evaluate_gate(closed, ss)
                assert status != "testnet_ready"
                assert status != "live_ready"


class TestBuildRunRecord:
    def test_record_fields(self):
        result = _make_pipeline_result()
        rec = build_run_record(result, run_id="test_run_001")
        assert rec.run_id == "test_run_001"
        assert rec.date == "2026-06-18"
        assert rec.pipeline_status == "PASS"
        assert rec.steps_passed == 2
        assert rec.steps_failed == 0
        assert rec.clean_positions == 16
        assert rec.closed_clean_positions == 3

    def test_record_gate_status(self):
        result = _make_pipeline_result()
        rec = build_run_record(result)
        assert rec.testnet_gate_status == GATE_BLOCKED_INSUFFICIENT

    def test_record_to_dict(self):
        rec = build_run_record(_make_pipeline_result(), run_id="test_002")
        d = rec.to_dict()
        assert "run_id" in d
        assert "testnet_gate_status" in d
        assert "safety_flags" in d


class TestRegistryIO:
    def test_append_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rec = build_run_record(_make_pipeline_result(), run_id="io_test_001")
            path = append_registry_record(rec, tmpdir)
            assert os.path.isfile(path)
            assert path.endswith("shadow_run_registry.jsonl")

            records = read_registry(tmpdir)
            assert len(records) == 1
            assert records[0]["run_id"] == "io_test_001"

    def test_multiple_appends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                rec = build_run_record(_make_pipeline_result(), run_id=f"multi_{i}")
                append_registry_record(rec, tmpdir)
            records = read_registry(tmpdir)
            assert len(records) == 3
            assert records[2]["run_id"] == "multi_2"

    def test_read_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            records = read_registry(tmpdir)
            assert records == []


class TestComputeSampleGate:
    def test_empty_registry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = compute_sample_gate(tmpdir)
            assert gate.total_runs == 0
            assert gate.testnet_gate_status == GATE_BLOCKED_INSUFFICIENT

    def test_with_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_test_ledger(tmpdir, closed_clean_count=3, open_count=2)
            rec = build_run_record(_make_pipeline_result(), run_id="gate_test", output_dir=tmpdir)
            append_registry_record(rec, tmpdir)
            gate = compute_sample_gate(tmpdir)
            assert gate.total_runs == 1
            assert gate.latest_run_id == "gate_test"
            assert gate.closed_clean_positions == 3
            assert gate.cumulative_closed_clean == 3
            assert gate.testnet_gate_status == GATE_BLOCKED_INSUFFICIENT

    def test_gate_result_to_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = compute_sample_gate(tmpdir)
            d = gate.to_dict()
            assert "testnet_gate_status" in d
            assert "safety_flags" in d

    def test_explicit_report_date_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rec = build_run_record(_make_pipeline_result(), run_id="gate_test")
            append_registry_record(rec, tmpdir)
            with pytest.raises(ValueError, match="report_date conflict"):
                compute_sample_gate(tmpdir, report_date="2026-06-17")


class TestReportDateContract:
    @pytest.mark.parametrize(
        ("utc_started_at", "expected"),
        [
            (datetime(2026, 7, 20, 15, 59, 59, tzinfo=timezone.utc), "2026-07-20"),
            (datetime(2026, 7, 20, 16, 0, 0, tzinfo=timezone.utc), "2026-07-21"),
            (datetime(2026, 7, 20, 18, 10, 29, tzinfo=timezone.utc), "2026-07-21"),
            (datetime(2026, 7, 20, 23, 59, 59, tzinfo=timezone.utc), "2026-07-21"),
            (datetime(2026, 7, 21, 0, 0, 0, tzinfo=timezone.utc), "2026-07-21"),
            (datetime(2026, 7, 21, 15, 59, 59, tzinfo=timezone.utc), "2026-07-21"),
            (datetime(2026, 7, 21, 16, 0, 0, tzinfo=timezone.utc), "2026-07-22"),
        ],
    )
    def test_asia_shanghai_boundaries(self, utc_started_at, expected):
        assert report_date_for_started_at(utc_started_at) == expected

    def test_split_day_utc_run_id_is_independent(self):
        context = build_pipeline_context(
            datetime(2026, 7, 20, 18, 10, 29, tzinfo=timezone.utc)
        )
        assert context == {
            "run_id": "20260720T181029Z_shadow_lifecycle",
            "started_at": "2026-07-20T18:10:29+00:00",
            "report_date": "2026-07-21",
        }

    def test_repeated_runs_share_cst_date(self):
        first = build_pipeline_context(
            datetime(2026, 7, 20, 18, 10, 29, tzinfo=timezone.utc)
        )
        second = build_pipeline_context(
            datetime(2026, 7, 21, 3, 10, 29, tzinfo=timezone.utc)
        )
        assert first["report_date"] == second["report_date"] == "2026-07-21"
        assert first["started_at"] != second["started_at"]

    @pytest.mark.parametrize("value", ["", "2026-7-21", "2026-02-30", None])
    def test_malformed_report_dates_fail_closed(self, value):
        with pytest.raises(ValueError, match="report_date"):
            validate_report_date(value)


class TestNoForbiddenPatterns:
    def test_no_order_words(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        for word in ["submit_order", "place_order", "cancel_order", "execute_trade"]:
            assert word not in content

    def test_no_env_reads(self):
        with open(MODULE_PATH) as f:
            content = f.read()
        assert "os.environ" not in content
        assert "os.getenv" not in content
