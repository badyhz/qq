from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import find_duplicate_candidate_ids, load_candidates, make_candidate_id, write_candidates


TERMINAL_STATUSES = {"SUBMITTED", "REJECTED", "EXPIRED", "SKIPPED", "SUBMIT_FAILED"}
NON_TERMINAL_STATUSES = {"PENDING", "APPROVED"}


def _now_utc_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_status(value: Any) -> str:
    return str(value or "").strip().upper()


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _build_unique_repaired_id(*, row: dict[str, Any], old_candidate_id: str, used_ids: set[str], index: int) -> str:
    symbol = str(row.get("symbol", "")).strip().upper()
    seed = "|".join(
        [
            "repair_duplicate_candidate_ids",
            old_candidate_id,
            str(row.get("ts_utc", "")),
            str(row.get("correlation_id", "")),
            str(index),
        ]
    )
    while True:
        new_id = make_candidate_id(symbol=symbol, seed=seed)
        if new_id not in used_ids:
            return new_id
        seed = seed + "|retry"


def repair_duplicate_candidate_ids(
    *,
    input_jsonl: str = "logs/execution_candidates.jsonl",
    output_jsonl: str = "logs/execution_candidates_repaired.jsonl",
    dry_run: bool = True,
    in_place: bool = False,
    action: str = "reject-pending",
    json_summary: bool = False,
) -> dict[str, Any]:
    resolved_action = str(action or "reject-pending").strip().lower()
    if resolved_action not in {"reject-pending", "rename-only", "expire-pending"}:
        summary = {"ok": False, "error": "unsupported_action", "action": resolved_action}
        if json_summary:
            print(json.dumps(summary, ensure_ascii=False))
        return summary

    input_path = str(input_jsonl or "logs/execution_candidates.jsonl")
    output_path = str(output_jsonl or "logs/execution_candidates_repaired.jsonl")
    input_abs = Path(input_path).resolve()
    output_abs = Path(output_path).resolve()

    if (not bool(in_place)) and input_abs == output_abs:
        summary = {"ok": False, "error": "output_matches_input_without_in_place", "input_jsonl": input_path, "output_jsonl": output_path}
        if json_summary:
            print(json.dumps(summary, ensure_ascii=False))
        return summary

    rows = load_candidates(input_path)
    duplicate_counts = find_duplicate_candidate_ids(rows)
    duplicate_ids = sorted(duplicate_counts.keys())
    duplicate_set = set(duplicate_ids)
    used_ids = {str(row.get("candidate_id", "")).strip() for row in rows if str(row.get("candidate_id", "")).strip()}

    repaired_rows = 0
    renamed_rows = 0
    rejected_rows = 0
    expired_rows = 0
    now_text = _now_utc_text()
    updated_rows: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        current = dict(row)
        current_id = str(current.get("candidate_id", "")).strip()
        status = _normalize_status(current.get("status", ""))

        should_repair = bool(current_id in duplicate_set and status in NON_TERMINAL_STATUSES)
        if should_repair:
            repaired_rows += 1
            old_candidate_id = current_id
            new_candidate_id = _build_unique_repaired_id(row=current, old_candidate_id=old_candidate_id, used_ids=used_ids, index=idx)
            current["candidate_id"] = new_candidate_id
            current["old_candidate_id"] = str(current.get("old_candidate_id", "")).strip() or old_candidate_id
            current["updated_at_utc"] = now_text
            used_ids.add(new_candidate_id)
            renamed_rows += 1

            if resolved_action == "reject-pending" and status == "PENDING":
                current["status"] = "REJECTED"
                current["rejected_reason"] = "repaired duplicate historical pending candidate"
                rejected_rows += 1
            elif resolved_action == "expire-pending" and status == "PENDING":
                current["status"] = "EXPIRED"
                current["expired_reason"] = "repaired duplicate historical pending candidate"
                expired_rows += 1
        updated_rows.append(current)

    output_target = input_path if bool(in_place) else output_path
    if (not bool(dry_run)) and output_target:
        write_candidates(output_target, updated_rows)

    post_duplicate_ids = sorted(find_duplicate_candidate_ids(updated_rows).keys())
    summary = {
        "ok": True,
        "input_jsonl": input_path,
        "output_jsonl": output_target,
        "dry_run": bool(dry_run),
        "in_place": bool(in_place),
        "action": resolved_action,
        "total_rows": len(rows),
        "duplicate_ids_count": len(duplicate_ids),
        "duplicate_ids": duplicate_ids,
        "repaired_rows": repaired_rows,
        "rejected_rows": rejected_rows,
        "expired_rows": expired_rows,
        "renamed_rows": renamed_rows,
        "post_repair_duplicate_ids_count": len(post_duplicate_ids),
        "post_repair_duplicate_ids": post_duplicate_ids,
        "wrote_file": bool((not bool(dry_run)) and bool(output_target)),
    }
    if json_summary:
        print(json.dumps(summary, ensure_ascii=False))
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repair historical duplicate execution candidate IDs safely")
    parser.add_argument("--input-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--output-jsonl", default="logs/execution_candidates_repaired.jsonl")
    parser.add_argument("--dry-run", nargs="?", const="true", default="true")
    parser.add_argument("--in-place", action="store_true")
    parser.add_argument("--action", choices=["reject-pending", "rename-only", "expire-pending"], default="reject-pending")
    parser.add_argument("--json-summary", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    summary = repair_duplicate_candidate_ids(
        input_jsonl=str(args.input_jsonl or "logs/execution_candidates.jsonl"),
        output_jsonl=str(args.output_jsonl or "logs/execution_candidates_repaired.jsonl"),
        dry_run=_to_bool(args.dry_run, default=True),
        in_place=bool(args.in_place),
        action=str(args.action or "reject-pending"),
        json_summary=bool(args.json_summary),
    )
    if not bool(args.json_summary):
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
