from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from core.execution_candidate_queue import apply_candidate_scoring, load_candidates, sort_candidates_for_review, write_candidates
from core.risk_event_logger import DEFAULT_RISK_EVENTS_PATH, log_risk_event


MUTABLE_STATUS = "PENDING"
TERMINAL_STATUSES = {"SUBMITTED", "SKIPPED"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_status(value: Any) -> str:
    return str(value or "").strip().upper()


def _candidate_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(row.get("candidate_id", "")),
        "symbol": str(row.get("symbol", "")),
        "side": str(row.get("side", "")),
        "notional_usdt": row.get("notional_usdt", 0),
        "status": _normalize_status(row.get("status", "")),
        "preflight_status": str(row.get("preflight_status", "")),
        "risk_flags": list(row.get("risk_flags", [])) if isinstance(row.get("risk_flags", []), list) else [],
        "expires_at_utc": str(row.get("expires_at_utc", "")),
        "signal_score": int(row.get("signal_score", 0) or 0),
        "signal_score_label": str(row.get("signal_score_label", "")),
        "execution_priority": int(row.get("execution_priority", row.get("signal_score", 0)) or 0),
    }


def list_execution_candidates(*, candidates_jsonl: str) -> dict[str, Any]:
    rows = load_candidates(candidates_jsonl)
    rows = apply_candidate_scoring(rows)
    rows = sort_candidates_for_review(rows)
    return {
        "ok": True,
        "action": "list",
        "candidates_jsonl": candidates_jsonl,
        "total": len(rows),
        "candidates": [_candidate_view(row) for row in rows],
    }


def show_execution_candidate(*, candidates_jsonl: str, candidate_id: str) -> dict[str, Any]:
    target = str(candidate_id or "").strip()
    matched: list[dict[str, Any]] = []
    for row in load_candidates(candidates_jsonl):
        if str(row.get("candidate_id", "")).strip() == target:
            matched.append(dict(row))
    if len(matched) > 1:
        return {
            "ok": False,
            "action": "show",
            "error": "ambiguous_candidate_id",
            "candidate_id": target,
            "matched_count": len(matched),
            "matched_candidates": [_candidate_view(row) for row in matched],
        }
    if len(matched) == 1:
        return {"ok": True, "action": "show", "candidate": matched[0]}
    return {"ok": False, "action": "show", "error": "candidate_not_found", "candidate_id": target}


def _transition_event_type(action: str) -> str:
    return {
        "approve": "CANDIDATE_APPROVED",
        "reject": "CANDIDATE_REJECTED",
        "expire": "CANDIDATE_EXPIRED",
    }.get(action, "CANDIDATE_UPDATED")


def _next_status(action: str) -> str:
    return {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "expire": "EXPIRED",
    }[action]


def transition_execution_candidate(
    *,
    candidates_jsonl: str,
    candidate_id: str,
    action: str,
    reason: str = "",
    approved_by: str = "winnie",
    risk_events_jsonl: str = DEFAULT_RISK_EVENTS_PATH,
) -> dict[str, Any]:
    resolved_action = str(action or "").strip().lower()
    if resolved_action not in {"approve", "reject", "expire"}:
        return {"ok": False, "action": resolved_action, "error": "unsupported_action"}

    rows = load_candidates(candidates_jsonl)
    target = str(candidate_id or "").strip()
    matched_indexes = [idx for idx, row in enumerate(rows) if str(row.get("candidate_id", "")).strip() == target]
    if len(matched_indexes) > 1:
        return {
            "ok": False,
            "action": resolved_action,
            "error": "ambiguous_candidate_id",
            "candidate_id": target,
            "matched_count": len(matched_indexes),
            "matched_candidates": [_candidate_view(rows[idx]) for idx in matched_indexes],
        }
    changed: dict[str, Any] | None = None
    previous_status = ""

    for row in rows:
        if str(row.get("candidate_id", "")).strip() != target:
            continue
        previous_status = _normalize_status(row.get("status", ""))
        if previous_status != MUTABLE_STATUS:
            return {
                "ok": False,
                "action": resolved_action,
                "candidate_id": target,
                "status": previous_status,
                "error": "candidate_status_not_mutable",
            }

        new_status = _next_status(resolved_action)
        row["status"] = new_status
        row["updated_at_utc"] = _now_utc()
        if resolved_action == "approve":
            row["approved_by"] = str(approved_by or "").strip() or "winnie"
            row["approved_at_utc"] = row["updated_at_utc"]
        elif resolved_action == "reject":
            row["rejected_reason"] = str(reason or "").strip() or "manual_reject"
        elif resolved_action == "expire":
            row["expired_reason"] = str(reason or "").strip() or "manual_expire"
        changed = dict(row)
        break

    if changed is None:
        return {"ok": False, "action": resolved_action, "error": "candidate_not_found", "candidate_id": target}

    write_candidates(candidates_jsonl, rows)
    event = log_risk_event(
        env=str(changed.get("env", "testnet")),
        symbol=str(changed.get("symbol", "")),
        component="manage_execution_candidates",
        event_type=_transition_event_type(resolved_action),
        message=f"candidate {resolved_action}d",
        context={
            "candidate_id": target,
            "previous_status": previous_status,
            "new_status": changed.get("status", ""),
            "reason": str(reason or ""),
            "approved_by": str(approved_by or ""),
        },
        action_required="none",
        correlation_id=target,
        output_path=risk_events_jsonl,
    )
    return {
        "ok": True,
        "action": resolved_action,
        "candidate_id": target,
        "previous_status": previous_status,
        "new_status": changed.get("status", ""),
        "candidate": changed,
        "event_type": event.get("event_type", ""),
    }


def manage_execution_candidates(
    *,
    candidates_jsonl: str,
    action: str,
    candidate_id: str = "",
    reason: str = "",
    approved_by: str = "winnie",
    risk_events_jsonl: str = DEFAULT_RISK_EVENTS_PATH,
) -> dict[str, Any]:
    resolved_action = str(action or "list").strip().lower()
    if resolved_action == "list":
        return list_execution_candidates(candidates_jsonl=candidates_jsonl)
    if resolved_action == "show":
        return show_execution_candidate(candidates_jsonl=candidates_jsonl, candidate_id=candidate_id)
    return transition_execution_candidate(
        candidates_jsonl=candidates_jsonl,
        candidate_id=candidate_id,
        action=resolved_action,
        reason=reason,
        approved_by=approved_by,
        risk_events_jsonl=risk_events_jsonl,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage execution candidate approval states")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--action", choices=["list", "show", "approve", "reject", "expire"], default="list")
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--approved-by", default="winnie")
    parser.add_argument("--risk-events-jsonl", default=DEFAULT_RISK_EVENTS_PATH)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = manage_execution_candidates(
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        action=str(args.action or "list"),
        candidate_id=str(args.candidate_id or ""),
        reason=str(args.reason or ""),
        approved_by=str(args.approved_by or "winnie"),
        risk_events_jsonl=str(args.risk_events_jsonl or DEFAULT_RISK_EVENTS_PATH),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
