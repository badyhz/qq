"""Tests for frozen human review queue — T15001."""
from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from core.frozen_human_review_queue import (
    FORBIDDEN_DECISIONS,
    POSSIBLE_DECISIONS,
    RELEASE_HOLD_REQUIRED,
    QueueItem,
    build_queue_from_matrix,
    build_queue_item,
    classify_priority,
    load_decision_matrix,
    render_queue_markdown,
    write_json,
    write_manifest,
    write_markdown,
)

FIXTURE_DIR = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "frozen_human_review_queue"
SAMPLE_MATRIX = FIXTURE_DIR / "sample_decision_matrix.json"


class TestPriorityClassification:
    def test_p0_submit(self):
        assert classify_priority(["submit"], "LIVE") == "P0_CRITICAL_REVIEW"

    def test_p0_cancel(self):
        assert classify_priority(["cancel"], "CANCEL") == "P0_CRITICAL_REVIEW"

    def test_p0_flatten(self):
        assert classify_priority(["flatten"], "FLATTEN") == "P0_CRITICAL_REVIEW"

    def test_p0_live(self):
        assert classify_priority(["live"], "LIVE") == "P0_CRITICAL_REVIEW"

    def test_p0_runtime(self):
        assert classify_priority(["runtime"], "RUNTIME") == "P0_CRITICAL_REVIEW"

    def test_p0_binance(self):
        assert classify_priority(["binance"], "LIVE") == "P0_CRITICAL_REVIEW"

    def test_p0_fapi(self):
        assert classify_priority(["fapi"], "LIVE") == "P0_CRITICAL_REVIEW"

    def test_p1_testnet(self):
        assert classify_priority(["testnet"], "TESTNET") == "P1_HIGH_REVIEW"

    def test_p1_order(self):
        assert classify_priority(["order"], "UNKNOWN") == "P1_HIGH_REVIEW"

    def test_p1_exchange(self):
        assert classify_priority(["exchange"], "UNKNOWN") == "P1_HIGH_REVIEW"

    def test_p2_shadow(self):
        assert classify_priority(["shadow"], "FLATTEN") == "P0_CRITICAL_REVIEW"

    def test_p2_observation(self):
        assert classify_priority(["observation"], "UNKNOWN") == "P2_STANDARD_REVIEW"

    def test_p2_verify(self):
        assert classify_priority(["verify"], "UNKNOWN") == "P2_STANDARD_REVIEW"

    def test_unknown_no_keywords(self):
        assert classify_priority([], "UNKNOWN") == "UNKNOWN_REVIEW"

    def test_p3_fallback(self):
        assert classify_priority(["research"], "RESEARCH") == "P3_LOW_REVIEW"


class TestQueueItemBuild:
    def test_basic_build(self):
        entry = {
            "path": "scripts/submit_approved_candidates.py",
            "exists": True,
            "category": "LIVE",
            "risk_score": 53,
            "risk_keywords": ["submit", "live"],
            "disposition": "CANDIDATE_FOR_ARCHIVE",
            "release_hold": "HOLD",
        }
        item = build_queue_item(0, entry, "HOLD")
        assert item.queue_id == "QR-0001"
        assert item.path == "scripts/submit_approved_candidates.py"
        assert item.priority == "P0_CRITICAL_REVIEW"
        assert item.no_touch_required is True
        assert item.no_execution is True
        assert item.no_import is True
        assert item.no_stage is True
        assert item.release_hold == "HOLD"
        assert item.advisory_only is True
        assert item.human_review_required is True

    def test_possible_decisions_safe_only(self):
        entry = {"path": "test.py", "category": "UNKNOWN", "risk_keywords": [], "disposition": "NEEDS_HUMAN_REVIEW"}
        item = build_queue_item(0, entry, "HOLD")
        for d in item.possible_decisions:
            assert d in POSSIBLE_DECISIONS

    def test_forbidden_decisions_include_activation(self):
        entry = {"path": "test.py", "category": "UNKNOWN", "risk_keywords": [], "disposition": "NEEDS_HUMAN_REVIEW"}
        item = build_queue_item(0, entry, "HOLD")
        for d in FORBIDDEN_DECISIONS:
            assert d in item.forbidden_decisions
        assert "EXECUTE" in item.forbidden_decisions
        assert "IMPORT" in item.forbidden_decisions
        assert "ACTIVATE_LIVE" in item.forbidden_decisions
        assert "ACTIVATE_TESTNET" in item.forbidden_decisions


class TestBuildQueueFromMatrix:
    def test_load_and_build(self):
        entries = load_decision_matrix(SAMPLE_MATRIX)
        items = build_queue_from_matrix(entries, release_hold="HOLD")
        assert len(items) == 5
        assert all(isinstance(i, QueueItem) for i in items)

    def test_release_hold_mismatch_fails(self):
        entries = [{"path": "test.py", "category": "X", "risk_keywords": [], "disposition": "Y"}]
        with pytest.raises(ValueError, match="release_hold"):
            build_queue_from_matrix(entries, release_hold="NOT_HOLD")

    def test_deterministic_output(self):
        entries = load_decision_matrix(SAMPLE_MATRIX)
        items1 = build_queue_from_matrix(entries, release_hold="HOLD")
        items2 = build_queue_from_matrix(entries, release_hold="HOLD")
        assert [i.to_dict() for i in items1] == [i.to_dict() for i in items2]


class TestNoTouchFlags:
    def test_all_no_touch_true(self):
        entries = load_decision_matrix(SAMPLE_MATRIX)
        items = build_queue_from_matrix(entries, release_hold="HOLD")
        for item in items:
            assert item.no_touch_required is True
            assert item.no_execution is True
            assert item.no_import is True
            assert item.no_stage is True


class TestWriteOutputs:
    def test_write_json(self):
        entries = load_decision_matrix(SAMPLE_MATRIX)
        items = build_queue_from_matrix(entries, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "queue.json"
            write_json(items, out)
            assert out.exists()
            data = json.loads(out.read_text())
            assert len(data) == len(items)

    def test_write_manifest(self):
        entries = load_decision_matrix(SAMPLE_MATRIX)
        items = build_queue_from_matrix(entries, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "manifest.json"
            write_manifest(items, out, "HOLD")
            data = json.loads(out.read_text())
            assert data["release_hold"] == "HOLD"
            assert data["total_items"] == len(items)

    def test_write_markdown(self):
        entries = load_decision_matrix(SAMPLE_MATRIX)
        items = build_queue_from_matrix(entries, release_hold="HOLD")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = pathlib.Path(tmpdir) / "queue.md"
            write_markdown(items, out)
            content = out.read_text()
            assert "Frozen File Human Review Queue" in content
            assert "No-Touch Statement" in content
