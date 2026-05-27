"""T1531 - Frozen Backlog Report JSON Renderer Tests.

At least 10 tests. Pure functions only. No I/O except tmp_path file write.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_full_report
from core.frozen_backlog_report_json import (
    render_record_dict,
    render_report_json,
    render_summary_dict,
)

_summary, _records = materialize_full_report(FROZEN_BACKLOG_INVENTORY)


# --- render_record_dict ---


class TestRenderRecordDict:
    def test_keys_present(self) -> None:
        d = render_record_dict(_records[0])
        expected = {
            "record_id",
            "file_path",
            "risk_class",
            "category",
            "allowed_actions",
            "forbidden_actions",
            "required_evidence",
            "readiness_score",
            "unlock_recommendation",
            "release_hold",
        }
        assert set(d.keys()) == expected

    def test_release_hold_is_hold(self) -> None:
        for record in _records:
            d = render_record_dict(record)
            assert d["release_hold"] == "HOLD"

    def test_allowed_actions_is_list(self) -> None:
        d = render_record_dict(_records[0])
        assert isinstance(d["allowed_actions"], list)

    def test_forbidden_actions_is_list(self) -> None:
        d = render_record_dict(_records[0])
        assert isinstance(d["forbidden_actions"], list)

    def test_required_evidence_is_list(self) -> None:
        d = render_record_dict(_records[0])
        assert isinstance(d["required_evidence"], list)

    def test_deterministic(self) -> None:
        a = render_record_dict(_records[0])
        b = render_record_dict(_records[0])
        assert a == b


# --- render_summary_dict ---


class TestRenderSummaryDict:
    def test_keys_present(self) -> None:
        d = render_summary_dict(_summary)
        expected = {
            "summary_id",
            "total_files",
            "high_risk_count",
            "medium_risk_count",
            "release_hold",
            "no_live",
            "no_submit",
            "no_exchange",
            "no_runtime_integration",
            "no_planner_integration",
        }
        assert set(d.keys()) == expected

    def test_total_files(self) -> None:
        d = render_summary_dict(_summary)
        assert d["total_files"] == 22

    def test_high_risk_count(self) -> None:
        d = render_summary_dict(_summary)
        assert d["high_risk_count"] == 9

    def test_medium_risk_count(self) -> None:
        d = render_summary_dict(_summary)
        assert d["medium_risk_count"] == 13

    def test_release_hold(self) -> None:
        d = render_summary_dict(_summary)
        assert d["release_hold"] == "HOLD"

    def test_no_live_true(self) -> None:
        d = render_summary_dict(_summary)
        assert d["no_live"] is True

    def test_deterministic(self) -> None:
        a = render_summary_dict(_summary)
        b = render_summary_dict(_summary)
        assert a == b


# --- render_report_json ---


class TestRenderReportJson:
    def test_valid_json(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        assert isinstance(parsed, dict)

    def test_has_summary_key(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        assert "summary" in parsed

    def test_has_records_key(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        assert "records" in parsed

    def test_records_length_22(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        assert len(parsed["records"]) == 22

    def test_summary_total_files(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        assert parsed["summary"]["total_files"] == 22

    def test_summary_high_risk_count(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        assert parsed["summary"]["high_risk_count"] == 9

    def test_summary_medium_risk_count(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        assert parsed["summary"]["medium_risk_count"] == 13

    def test_deterministic(self) -> None:
        a = render_report_json(_summary, _records)
        b = render_report_json(_summary, _records)
        assert a == b

    def test_key_ordering(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_write_to_file(self, tmp_path: object) -> None:
        """Verify JSON can be written to file and re-read."""
        raw = render_report_json(_summary, _records)
        out = pathlib.Path(str(tmp_path)) / "report.json"
        out.write_text(raw, encoding="utf-8")
        assert out.exists()
        reloaded = json.loads(out.read_text(encoding="utf-8"))
        assert reloaded["summary"]["total_files"] == 22

    def test_all_records_have_hold(self) -> None:
        raw = render_report_json(_summary, _records)
        parsed = json.loads(raw)
        for rec in parsed["records"]:
            assert rec["release_hold"] == "HOLD"
