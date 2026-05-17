from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_testnet_artifacts import validate_testnet_artifacts


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_minimal_logs(root: Path, date: str = "2026-05-17") -> None:
    _write(root / "execution_candidates.jsonl", '{"status":"approved"}\n')
    _write(root / "risk_events.jsonl", '{"event_type":"X"}\n')
    _write(root / "risk_events_scoped_v3.jsonl", '{"event_type":"Y"}\n')
    _write(root / f"daily_summary_{date}.md", "ok\n")

    run = root / "approved_candidate_runs" / "run1"
    _write(run / "summary.json", json.dumps({"run_id": "run1", "overall_status": "PASS", "planned_count": 0, "submitted_count": 0, "failed_count": 0}))
    _write(run / "summary.md", "ok\n")
    _write(run / "acceptance_report.md", "ok\n")
    _write(run / "approved_payloads.jsonl", "")

    obs = root / "observation_shifts" / "obs1"
    _write(obs / "summary.json", "{}")
    _write(obs / "summary.md", "ok\n")

    sch = root / "scheduled_observations" / "sch1"
    _write(sch / "summary.json", "{}")
    _write(sch / "summary.md", "ok\n")


def test_all_required_artifacts_present_pass(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    _seed_minimal_logs(logs)
    summary = validate_testnet_artifacts(logs_dir=str(logs), date="2026-05-17", strict=True)
    assert summary["ok"] is True
    assert summary["verdict"] == "PASS"
    assert summary["missing_files"] == []
    assert summary["invalid_json_files"] == []


def test_missing_artifact_fails_in_strict_mode(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    _seed_minimal_logs(logs)
    (logs / "risk_events_scoped_v3.jsonl").unlink()
    summary = validate_testnet_artifacts(logs_dir=str(logs), date="2026-05-17", strict=True)
    assert summary["ok"] is False
    assert summary["verdict"] == "FAIL"
    assert any("risk_events_scoped_v3.jsonl" in p for p in summary["missing_files"])


def test_invalid_jsonl_shape_fails(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    _seed_minimal_logs(logs)
    _write(logs / "risk_events.jsonl", '{"event_type":"ok"}\nnot-json\n')
    summary = validate_testnet_artifacts(logs_dir=str(logs), date="2026-05-17", strict=False)
    assert summary["ok"] is False
    assert summary["verdict"] == "FAIL"
    assert summary["invalid_json_files"]


def test_partial_when_non_strict_with_missing_files(tmp_path: Path) -> None:
    logs = tmp_path / "logs"
    _seed_minimal_logs(logs)
    (logs / "approved_candidate_runs" / "run1" / "summary.md").unlink()
    summary = validate_testnet_artifacts(logs_dir=str(logs), date="2026-05-17", strict=False)
    assert summary["ok"] is True
    assert summary["verdict"] == "PARTIAL"
    assert summary["missing_files"]
