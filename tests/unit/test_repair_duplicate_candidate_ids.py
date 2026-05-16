from __future__ import annotations

import json
from pathlib import Path

from core.execution_candidate_queue import load_candidates
from scripts.repair_duplicate_candidate_ids import repair_duplicate_candidate_ids


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_repair_duplicate_candidate_ids_reject_pending_dry_run(tmp_path: Path) -> None:
    input_jsonl = tmp_path / "candidates.jsonl"
    rows = [
        {
            "candidate_id": "cand_dup_1",
            "symbol": "BTCUSDT",
            "status": "PENDING",
            "ts_utc": "2026-01-01T00:00:00+00:00",
            "correlation_id": "corr-a",
        },
        {
            "candidate_id": "cand_dup_1",
            "symbol": "BTCUSDT",
            "status": "SUBMITTED",
            "ts_utc": "2026-01-01T00:01:00+00:00",
            "correlation_id": "corr-b",
        },
    ]
    _write_jsonl(input_jsonl, rows)

    summary = repair_duplicate_candidate_ids(
        input_jsonl=str(input_jsonl),
        output_jsonl=str(tmp_path / "repaired.jsonl"),
        dry_run=True,
        in_place=False,
        action="reject-pending",
    )

    assert summary["ok"] is True
    assert summary["duplicate_ids_count"] == 1
    assert summary["repaired_rows"] == 1
    assert summary["renamed_rows"] == 1
    assert summary["rejected_rows"] == 1
    assert summary["post_repair_duplicate_ids_count"] == 0
    assert summary["wrote_file"] is False
    assert not (tmp_path / "repaired.jsonl").exists()


def test_repair_duplicate_candidate_ids_rename_only_writes_output(tmp_path: Path) -> None:
    input_jsonl = tmp_path / "candidates.jsonl"
    output_jsonl = tmp_path / "repaired.jsonl"
    rows = [
        {
            "candidate_id": "cand_dup_2",
            "symbol": "ETHUSDT",
            "status": "APPROVED",
            "ts_utc": "2026-01-01T00:00:00+00:00",
            "correlation_id": "corr-c",
        },
        {
            "candidate_id": "cand_dup_2",
            "symbol": "ETHUSDT",
            "status": "SUBMITTED",
            "ts_utc": "2026-01-01T00:01:00+00:00",
            "correlation_id": "corr-d",
        },
    ]
    _write_jsonl(input_jsonl, rows)

    summary = repair_duplicate_candidate_ids(
        input_jsonl=str(input_jsonl),
        output_jsonl=str(output_jsonl),
        dry_run=False,
        in_place=False,
        action="rename-only",
    )

    assert summary["ok"] is True
    assert summary["wrote_file"] is True
    assert summary["repaired_rows"] == 1
    assert summary["renamed_rows"] == 1
    assert summary["rejected_rows"] == 0
    assert summary["expired_rows"] == 0

    out_rows = load_candidates(str(output_jsonl))
    assert len(out_rows) == 2
    approved_rows = [row for row in out_rows if str(row.get("status", "")).upper() == "APPROVED"]
    assert len(approved_rows) == 1
    repaired = approved_rows[0]
    assert repaired["candidate_id"] != "cand_dup_2"
    assert repaired["old_candidate_id"] == "cand_dup_2"


def test_repair_duplicate_candidate_ids_rejects_same_output_without_in_place(tmp_path: Path) -> None:
    input_jsonl = tmp_path / "candidates.jsonl"
    _write_jsonl(
        input_jsonl,
        [{"candidate_id": "cand_x", "symbol": "SOLUSDT", "status": "PENDING", "ts_utc": "2026-01-01T00:00:00+00:00"}],
    )

    summary = repair_duplicate_candidate_ids(
        input_jsonl=str(input_jsonl),
        output_jsonl=str(input_jsonl),
        dry_run=True,
        in_place=False,
        action="reject-pending",
    )

    assert summary["ok"] is False
    assert summary["error"] == "output_matches_input_without_in_place"
