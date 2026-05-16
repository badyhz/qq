from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from core.execution_candidate_queue import apply_candidate_scoring, sort_candidates_for_review
from core.trade_logger import read_jsonl_rows


ACTIVE_STATUSES = {"PENDING", "APPROVED"}


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return bool(default)


def _candidate_view(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(row.get("candidate_id", "")),
        "symbol": str(row.get("symbol", "")),
        "status": str(row.get("status", "")),
        "signal_score": int(row.get("signal_score", 0) or 0),
        "signal_score_label": str(row.get("signal_score_label", "")),
        "execution_priority": int(row.get("execution_priority", row.get("signal_score", 0)) or 0),
        "signal_score_reasons": list(row.get("signal_score_reasons", [])) if isinstance(row.get("signal_score_reasons", []), list) else [],
        "risk_flags": list(row.get("risk_flags", [])) if isinstance(row.get("risk_flags", []), list) else [],
        "notional_usdt": row.get("notional_usdt", 0),
        "ts_utc": str(row.get("ts_utc", "")),
    }


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Candidate Quality Report",
        "",
        f"- verdict: {report.get('verdict', '')}",
        f"- recommendation: {','.join(list(report.get('recommendations', [])))}",
        f"- total_candidates: {report.get('total_candidates', 0)}",
        f"- active_candidates: {report.get('active_candidates', 0)}",
        f"- high_count: {report.get('high_count', 0)}",
        f"- medium_count: {report.get('medium_count', 0)}",
        f"- low_count: {report.get('low_count', 0)}",
        f"- blocked_count: {report.get('blocked_count', 0)}",
        "",
        "## Top Candidates",
    ]
    for row in list(report.get("top_candidates", [])):
        lines.append(f"- {row.get('candidate_id', '')} {row.get('symbol', '')} score={row.get('signal_score', 0)} label={row.get('signal_score_label', '')}")
    lines.extend(["", "## Blocked Candidates"])
    for row in list(report.get("blocked_candidates", [])):
        lines.append(f"- {row.get('candidate_id', '')} {row.get('symbol', '')} reasons={json.dumps(row.get('signal_score_reasons', []), ensure_ascii=False)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_candidate_quality_report(
    *,
    candidates_jsonl: str = "logs/execution_candidates.jsonl",
    include_terminal: bool = False,
    output_md: str = "logs/candidate_quality_report.md",
    json_output: bool = False,
) -> dict[str, Any]:
    raw_rows = [row for row in read_jsonl_rows(candidates_jsonl) if isinstance(row, dict)]
    scored = sort_candidates_for_review(apply_candidate_scoring(raw_rows))
    if bool(include_terminal):
        active_rows = scored
    else:
        active_rows = [row for row in scored if str(row.get("status", "")).strip().upper() in ACTIVE_STATUSES]

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "BLOCKED": 0}
    for row in active_rows:
        label = str(row.get("signal_score_label", "")).strip().upper()
        if label in counts:
            counts[label] += 1

    top_candidates = [_candidate_view(row) for row in active_rows[:10]]
    blocked_candidates = [_candidate_view(row) for row in active_rows if str(row.get("signal_score_label", "")).strip().upper() == "BLOCKED"]
    terminal_summary: dict[str, int] = {}
    for row in scored:
        status = str(row.get("status", "")).strip().upper()
        terminal_summary[status] = int(terminal_summary.get(status, 0)) + 1

    recommendations: list[str] = []
    verdict = "PARTIAL"
    if len(active_rows) == 0:
        verdict = "PASS"
        recommendations.append("no_active_candidates")
    else:
        if counts["HIGH"] > 0 or counts["MEDIUM"] > 0:
            recommendations.append("review_top_candidate")
        if counts["BLOCKED"] > 0:
            recommendations.append("do_not_approve_blocked_candidates")
        if not recommendations:
            recommendations.append("review_candidates")

    report = {
        "ok": True,
        "candidates_jsonl": candidates_jsonl,
        "include_terminal": bool(include_terminal),
        "total_candidates": len(scored),
        "active_candidates": len(active_rows),
        "high_count": counts["HIGH"],
        "medium_count": counts["MEDIUM"],
        "low_count": counts["LOW"],
        "blocked_count": counts["BLOCKED"],
        "top_candidates": top_candidates,
        "blocked_candidates": blocked_candidates,
        "terminal_candidates_summary": terminal_summary,
        "recommendations": recommendations,
        "verdict": verdict,
        "output_md": output_md,
    }
    _write_markdown(Path(output_md), report)
    if json_output:
        print(json.dumps(report, ensure_ascii=False))
    return report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate candidate quality and approval recommendation report")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--include-terminal", default="false")
    parser.add_argument("--output-md", default="logs/candidate_quality_report.md")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    generate_candidate_quality_report(
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        include_terminal=_to_bool(args.include_terminal, default=False),
        output_md=str(args.output_md or "logs/candidate_quality_report.md"),
        json_output=bool(args.json),
    )


if __name__ == "__main__":
    main()
