from __future__ import annotations

import json
from pathlib import Path

from core.execution_candidate_queue import load_candidates
from scripts.manage_execution_candidates import manage_execution_candidates


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_approve_reject_expire_and_risk_event_log(tmp_path: Path) -> None:
    candidates_jsonl = tmp_path / "candidates.jsonl"
    risk_events_jsonl = tmp_path / "risk_events.jsonl"
    _write_jsonl(
        candidates_jsonl,
        [
            {"candidate_id": "cand_a", "symbol": "BTCUSDT", "status": "PENDING", "env": "testnet"},
            {"candidate_id": "cand_b", "symbol": "ETHUSDT", "status": "PENDING", "env": "testnet"},
            {"candidate_id": "cand_c", "symbol": "SOLUSDT", "status": "PENDING", "env": "testnet"},
        ],
    )

    res_approve = manage_execution_candidates(
        candidates_jsonl=str(candidates_jsonl),
        action="approve",
        candidate_id="cand_a",
        approved_by="qa",
        risk_events_jsonl=str(risk_events_jsonl),
    )
    assert res_approve["ok"] is True
    assert res_approve["new_status"] == "APPROVED"

    res_reject = manage_execution_candidates(
        candidates_jsonl=str(candidates_jsonl),
        action="reject",
        candidate_id="cand_b",
        reason="manual_check",
        approved_by="qa",
        risk_events_jsonl=str(risk_events_jsonl),
    )
    assert res_reject["ok"] is True
    assert res_reject["new_status"] == "REJECTED"

    res_expire = manage_execution_candidates(
        candidates_jsonl=str(candidates_jsonl),
        action="expire",
        candidate_id="cand_c",
        approved_by="qa",
        risk_events_jsonl=str(risk_events_jsonl),
    )
    assert res_expire["ok"] is True
    assert res_expire["new_status"] == "EXPIRED"

    rows = load_candidates(str(candidates_jsonl))
    status_map = {str(r.get("candidate_id")): str(r.get("status")) for r in rows}
    assert status_map == {"cand_a": "APPROVED", "cand_b": "REJECTED", "cand_c": "EXPIRED"}

    assert risk_events_jsonl.exists()
    event_lines = [line for line in risk_events_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(event_lines) == 3


def test_not_found_and_ambiguous_paths(tmp_path: Path) -> None:
    candidates_jsonl = tmp_path / "candidates.jsonl"
    risk_events_jsonl = tmp_path / "risk_events.jsonl"
    _write_jsonl(
        candidates_jsonl,
        [
            {"candidate_id": "dup", "symbol": "BTCUSDT", "status": "PENDING", "env": "testnet"},
            {"candidate_id": "dup", "symbol": "ETHUSDT", "status": "PENDING", "env": "testnet"},
            {"candidate_id": "single", "symbol": "SOLUSDT", "status": "SUBMITTED", "env": "testnet"},
        ],
    )

    ambiguous = manage_execution_candidates(
        candidates_jsonl=str(candidates_jsonl),
        action="approve",
        candidate_id="dup",
        approved_by="qa",
        risk_events_jsonl=str(risk_events_jsonl),
    )
    assert ambiguous["ok"] is False
    assert ambiguous["error"] == "ambiguous_candidate_id"

    not_found = manage_execution_candidates(
        candidates_jsonl=str(candidates_jsonl),
        action="reject",
        candidate_id="missing",
        approved_by="qa",
        risk_events_jsonl=str(risk_events_jsonl),
    )
    assert not_found["ok"] is False
    assert not_found["error"] == "candidate_not_found"

    not_mutable = manage_execution_candidates(
        candidates_jsonl=str(candidates_jsonl),
        action="expire",
        candidate_id="single",
        approved_by="qa",
        risk_events_jsonl=str(risk_events_jsonl),
    )
    assert not_mutable["ok"] is False
    assert not_mutable["error"] == "candidate_status_not_mutable"
