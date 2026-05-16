from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import load_candidates
from scripts.strategy_edge_common import parse_dt, read_csv_rows


FIELDS = [
    "candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "candidate_status",
    "last_gate_decision",
    "last_gate_reason",
    "recovery_decision",
    "recovery_reason",
    "suggested_status",
    "notes",
]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    except OSError:
        return []
    return rows


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"BUY", "LONG"}:
        return "LONG"
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    return text or "LONG"


def _candidate_strategy_key(candidate: dict[str, Any]) -> tuple[str, str, str, str]:
    symbol = str(candidate.get("symbol", "")).strip().upper()
    side = _normalize_side(candidate.get("side", "BUY"))
    timeframe = str(candidate.get("timeframe", candidate.get("signal_timeframe", "5m")) or "5m").strip() or "5m"
    strategy_key = str(candidate.get("strategy_key", "")).strip()
    if not strategy_key and symbol:
        strategy_key = f"{symbol}_{side}_{timeframe}"
    return symbol, side, timeframe, strategy_key


def _latest_audit_by_candidate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = str(row.get("candidate_id", "")).strip()
        if not cid:
            continue
        latest[cid] = row
    return latest


def evaluate_candidate_recovery_rules(
    *,
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    gate_audit_jsonl: str = "logs/gate_audit/gate_audit.jsonl",
    strategy_candidate_csv: str = "reports/strategy_candidate_score/strategy_candidate_score.csv",
    symbol_side_csv: str = "reports/symbol_side_recommendations/symbol_side_recommendations.csv",
    strategy_promotion_csv: str = "reports/strategy_promotion/strategy_promotion_decisions.csv",
    system_health_json: str = "reports/system_health/trading_system_health_dashboard.json",
    output_dir: str = "reports/candidate_recovery",
) -> dict[str, Any]:
    candidates = load_candidates(candidates_jsonl)
    gate_audit_rows = _load_jsonl(Path(gate_audit_jsonl))
    gate_latest = _latest_audit_by_candidate(gate_audit_rows)
    strategy_rows = read_csv_rows(Path(strategy_candidate_csv))
    symbol_side_rows = read_csv_rows(Path(symbol_side_csv))
    promotion_rows = read_csv_rows(Path(strategy_promotion_csv))
    system_health = _load_json(Path(system_health_json))

    strategy_index = {str(row.get("strategy_key", "")).strip(): row for row in strategy_rows if str(row.get("strategy_key", "")).strip()}
    symbol_side_index = {
        (
            str(row.get("symbol", "")).strip().upper(),
            str(row.get("side", "")).strip().upper(),
            str(row.get("timeframe", "5m")).strip(),
        ): row
        for row in symbol_side_rows
    }
    promotion_index = {str(row.get("strategy_key", "")).strip(): row for row in promotion_rows if str(row.get("strategy_key", "")).strip()}

    health_verdict = str(system_health.get("final_verdict", "UNKNOWN")).strip().upper()
    health_next_action = str(system_health.get("next_action", "")).strip().upper()
    now = datetime.now(timezone.utc)

    out_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        current = dict(candidate)
        candidate_id = str(current.get("candidate_id", "")).strip()
        status = str(current.get("status", "")).strip().upper()
        symbol, side, timeframe, strategy_key = _candidate_strategy_key(current)
        strategy_row = strategy_index.get(strategy_key, {})
        symbol_row = symbol_side_index.get((symbol, side, timeframe), {})
        promotion_row = promotion_index.get(strategy_key, {})
        audit = gate_latest.get(candidate_id, {})
        audit_reasons = audit.get("reason", [])
        if not isinstance(audit_reasons, list):
            audit_reasons = [str(audit_reasons)] if str(audit_reasons).strip() else []
        reasons: set[str] = set(str(item).strip() for item in audit_reasons if str(item).strip())

        if health_verdict == "FAIL":
            reasons.add("system_health_fail")
        if health_next_action == "DO_NOT_SUBMIT_TODAY_MAX_DAILY_SUBMITS_REACHED":
            reasons.add("max_daily_submits_reached")
        if str(strategy_row.get("sample_confidence_level", "")).strip().upper() == "TOO_SMALL":
            reasons.add("sample_size_too_small")
        recommendation = str(symbol_row.get("recommendation", "UNKNOWN")).strip().upper()
        if recommendation in {"BLACKLIST", "REJECT", "PAUSE"}:
            reasons.add("symbol_side_rejected")
        promotion_decision = str(promotion_row.get("promotion_decision", "UNKNOWN")).strip().upper()
        if promotion_decision in {"REJECT_STRATEGY", "PAUSE_STRATEGY"}:
            reasons.add("strategy_rejected")

        ts = parse_dt(current.get("ts_utc", ""))
        if status == "EXPIRED":
            reasons.add("candidate_too_old")
        elif ts is not None and ts < (now - timedelta(hours=48)):
            reasons.add("candidate_too_old")

        notes: list[str] = []
        if status == "BLOCKED_BY_STRATEGY_GATE" and not audit:
            reasons.add("missing_gate_audit")
            notes.append("blocked_candidate_without_audit")

        decision = "UNKNOWN"
        suggested_status = status or "UNKNOWN"
        recovery_reason = "insufficient_context"

        if "missing_gate_audit" in reasons:
            decision = "REQUIRE_MANUAL_REVIEW"
            recovery_reason = "missing_gate_audit"
            suggested_status = "WATCHING"
        elif "system_health_fail" in reasons:
            decision = "KEEP_BLOCKED"
            recovery_reason = "system_health_fail"
            suggested_status = "BLOCKED_BY_STRATEGY_GATE"
        elif "symbol_side_rejected" in reasons or "strategy_rejected" in reasons:
            if "candidate_too_old" in reasons:
                decision = "EXPIRE_CANDIDATE"
                recovery_reason = "symbol_or_strategy_rejected_and_too_old"
                suggested_status = "EXPIRED"
            else:
                decision = "KEEP_BLOCKED"
                recovery_reason = "symbol_or_strategy_rejected"
                suggested_status = "BLOCKED_BY_STRATEGY_GATE"
        elif "sample_size_too_small" in reasons:
            decision = "RECOVER_TO_WATCHING"
            recovery_reason = "collect_more_samples"
            suggested_status = "WATCHING"
        elif reasons and reasons.issubset({"max_daily_submits_reached"}):
            decision = "RECOVER_TO_PENDING"
            recovery_reason = "submit_limit_reset_needed"
            suggested_status = "PENDING"
        elif "candidate_too_old" in reasons:
            decision = "EXPIRE_CANDIDATE"
            recovery_reason = "candidate_too_old"
            suggested_status = "EXPIRED"
        elif not reasons:
            decision = "RECOVER_TO_PENDING" if status in {"APPROVED", "PENDING"} else "RECOVER_TO_WATCHING"
            recovery_reason = "no_gate_block_reason_detected"
            suggested_status = "PENDING" if status in {"APPROVED", "PENDING"} else "WATCHING"

        out_rows.append(
            {
                "candidate_id": candidate_id,
                "symbol": symbol,
                "side": side,
                "timeframe": timeframe,
                "strategy_key": strategy_key,
                "candidate_status": status,
                "last_gate_decision": str(audit.get("gate_decision", "UNKNOWN")).strip().upper() if audit else "UNKNOWN",
                "last_gate_reason": ";".join(sorted(reasons)),
                "recovery_decision": decision,
                "recovery_reason": recovery_reason,
                "suggested_status": suggested_status,
                "notes": ";".join(sorted(set(notes))),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "candidate_recovery_decisions.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out_rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(out_rows),
        "keep_blocked_count": sum(1 for row in out_rows if str(row.get("recovery_decision", "")).upper() == "KEEP_BLOCKED"),
        "recover_to_pending_count": sum(1 for row in out_rows if str(row.get("recovery_decision", "")).upper() == "RECOVER_TO_PENDING"),
        "recover_to_watching_count": sum(1 for row in out_rows if str(row.get("recovery_decision", "")).upper() == "RECOVER_TO_WATCHING"),
        "require_manual_review_count": sum(1 for row in out_rows if str(row.get("recovery_decision", "")).upper() == "REQUIRE_MANUAL_REVIEW"),
        "expire_candidate_count": sum(1 for row in out_rows if str(row.get("recovery_decision", "")).upper() == "EXPIRE_CANDIDATE"),
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS" if summary["candidate_count"] > 0 else "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Candidate Recovery Summary",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- candidate_count: {summary['candidate_count']}",
        f"- keep_blocked_count: {summary['keep_blocked_count']}",
        f"- recover_to_pending_count: {summary['recover_to_pending_count']}",
        f"- recover_to_watching_count: {summary['recover_to_watching_count']}",
        f"- require_manual_review_count: {summary['require_manual_review_count']}",
        f"- expire_candidate_count: {summary['expire_candidate_count']}",
    ]
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate blocked/expired candidate recovery rules")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--gate-audit-jsonl", default="logs/gate_audit/gate_audit.jsonl")
    parser.add_argument("--strategy-candidate-csv", default="reports/strategy_candidate_score/strategy_candidate_score.csv")
    parser.add_argument("--symbol-side-csv", default="reports/symbol_side_recommendations/symbol_side_recommendations.csv")
    parser.add_argument("--strategy-promotion-csv", default="reports/strategy_promotion/strategy_promotion_decisions.csv")
    parser.add_argument("--system-health-json", default="reports/system_health/trading_system_health_dashboard.json")
    parser.add_argument("--output-dir", default="reports/candidate_recovery")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = evaluate_candidate_recovery_rules(
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        gate_audit_jsonl=str(args.gate_audit_jsonl or "logs/gate_audit/gate_audit.jsonl"),
        strategy_candidate_csv=str(args.strategy_candidate_csv or "reports/strategy_candidate_score/strategy_candidate_score.csv"),
        symbol_side_csv=str(args.symbol_side_csv or "reports/symbol_side_recommendations/symbol_side_recommendations.csv"),
        strategy_promotion_csv=str(args.strategy_promotion_csv or "reports/strategy_promotion/strategy_promotion_decisions.csv"),
        system_health_json=str(args.system_health_json or "reports/system_health/trading_system_health_dashboard.json"),
        output_dir=str(args.output_dir or "reports/candidate_recovery"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"candidate_count={result.get('candidate_count', 0)}")
    print(f"recover_to_watching_count={result.get('recover_to_watching_count', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
