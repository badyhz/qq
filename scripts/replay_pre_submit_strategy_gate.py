from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import load_candidates
from scripts.pre_submit_strategy_gate import pre_submit_strategy_gate


FIELDS = [
    "candidate_id",
    "symbol",
    "side",
    "timeframe",
    "strategy_key",
    "candidate_status",
    "gate_decision",
    "submit_allowed",
    "dry_run_allowed",
    "reason",
    "would_block",
    "would_allow_dry_run",
    "required_next_samples",
]

BLOCK_DECISIONS = [
    "BLOCK_LOW_SAMPLE",
    "BLOCK_SYSTEM_HEALTH",
    "BLOCK_SYMBOL_SIDE",
    "BLOCK_STRATEGY_REJECTED",
    "BLOCK_UNKNOWN",
]


def _normalize_side(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"SELL", "SHORT"}:
        return "SHORT"
    if text in {"BUY", "LONG"}:
        return "LONG"
    return text or "LONG"


def _derive_strategy_fields(candidate: dict[str, Any]) -> dict[str, str]:
    symbol = str(candidate.get("symbol", "")).strip().upper()
    side = _normalize_side(candidate.get("side", "BUY"))
    timeframe = str(candidate.get("timeframe", candidate.get("signal_timeframe", "5m")) or "5m").strip() or "5m"
    strategy_key = str(candidate.get("strategy_key", "")).strip()
    if not strategy_key and symbol:
        strategy_key = f"{symbol}_{side}_{timeframe}"
    return {
        "symbol": symbol,
        "side": side,
        "timeframe": timeframe,
        "strategy_key": strategy_key,
    }


def replay_pre_submit_strategy_gate(
    *,
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    reports_dir: str = "reports",
    logs_dir: str = "logs",
    output_dir: str = "reports/gate_replay",
) -> dict[str, Any]:
    candidates = load_candidates(candidates_jsonl)
    rows: list[dict[str, Any]] = []

    for candidate in candidates:
        current = dict(candidate)
        fields = _derive_strategy_fields(current)
        gate_result = pre_submit_strategy_gate(
            candidate_id=str(current.get("candidate_id", "")).strip(),
            symbol=fields["symbol"],
            side=fields["side"],
            timeframe=fields["timeframe"],
            strategy_key=fields["strategy_key"],
            reports_dir=reports_dir,
            logs_dir=logs_dir,
        )
        gate_decision = str(gate_result.get("gate_decision", "BLOCK_UNKNOWN")).strip().upper()
        submit_allowed = bool(gate_result.get("submit_allowed", False))
        dry_run_allowed = bool(gate_result.get("dry_run_allowed", True))
        reason = gate_result.get("reason", [])
        reason_list = [str(item).strip() for item in (reason if isinstance(reason, list) else [reason]) if str(item).strip()]
        rows.append(
            {
                "candidate_id": str(current.get("candidate_id", "")).strip(),
                "symbol": fields["symbol"],
                "side": fields["side"],
                "timeframe": fields["timeframe"],
                "strategy_key": fields["strategy_key"],
                "candidate_status": str(current.get("status", "")).strip().upper(),
                "gate_decision": gate_decision,
                "submit_allowed": submit_allowed,
                "dry_run_allowed": dry_run_allowed,
                "reason": ";".join(sorted(set(reason_list))),
                "would_block": gate_decision.startswith("BLOCK_"),
                "would_allow_dry_run": dry_run_allowed,
                "required_next_samples": int(gate_result.get("required_next_samples", 0) or 0),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "gate_replay_results.csv"
    summary_json = out_dir / "summary.json"
    summary_md = out_dir / "summary.md"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    block_by_decision = {key: 0 for key in BLOCK_DECISIONS}
    for row in rows:
        decision = str(row.get("gate_decision", "")).strip().upper()
        if decision in block_by_decision and bool(row.get("would_block", False)):
            block_by_decision[decision] = int(block_by_decision[decision]) + 1

    summary = {
        "ok": True,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(rows),
        "would_block_count": sum(1 for row in rows if bool(row.get("would_block", False))),
        "would_allow_dry_run_count": sum(1 for row in rows if bool(row.get("would_allow_dry_run", False))),
        "would_allow_submit_count": sum(1 for row in rows if bool(row.get("submit_allowed", False))),
        "block_by_decision": block_by_decision,
        "csv_path": str(csv_path),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
    }
    summary["final_verdict"] = "PASS" if summary["candidate_count"] > 0 else "PARTIAL"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Strategy Gate Replay",
        "",
        f"- final_verdict: {summary['final_verdict']}",
        f"- candidate_count: {summary['candidate_count']}",
        f"- would_block_count: {summary['would_block_count']}",
        f"- would_allow_dry_run_count: {summary['would_allow_dry_run_count']}",
        f"- would_allow_submit_count: {summary['would_allow_submit_count']}",
    ]
    for key in BLOCK_DECISIONS:
        lines.append(f"- {key}: {int(block_by_decision.get(key, 0))}")
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run replay for pre-submit strategy gate")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--output-dir", default="reports/gate_replay")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = replay_pre_submit_strategy_gate(
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        reports_dir=str(args.reports_dir or "reports"),
        logs_dir=str(args.logs_dir or "logs"),
        output_dir=str(args.output_dir or "reports/gate_replay"),
    )
    if bool(args.json):
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"candidate_count={result.get('candidate_count', 0)}")
    print(f"would_block_count={result.get('would_block_count', 0)}")
    print(f"csv_path={result.get('csv_path', '')}")


if __name__ == "__main__":
    main()
