from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.strategy_edge_common import read_jsonl_rows


def _load_text(path: str) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _row_val(row: dict[str, Any], key: str, default: Any) -> Any:
    if key in row:
        return row[key]
    return default


def _risk_lines(path: str, max_events: int) -> tuple[str, dict[str, int]]:
    rows = read_jsonl_rows(Path(path)) if path else []
    totals: dict[str, int] = {}
    lines: list[str] = []
    limit = max(0, int(max_events))
    for row in rows[-limit:]:
        level = str(_row_val(row, "severity", "UNKNOWN") or "UNKNOWN").upper()
        totals[level] = int(totals[level] if level in totals else 0) + 1
        kind = str(_row_val(row, "event_type", ""))
        text = str(_row_val(row, "message", ""))
        lines.append(f"[{level}] {kind}: {text}")
    return "\n".join(lines), totals


def _candidate_counts(path: str) -> dict[str, int]:
    rows = read_jsonl_rows(Path(path)) if path else []
    out = {
        "total": len(rows),
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "expired": 0,
        "submitted": 0,
        "skipped": 0,
    }
    for row in rows:
        status = str(_row_val(row, "status", "")).strip().upper().lower()
        if status in out:
            out[status] = int(out[status]) + 1
    return out


def _trim_text(text: str, max_chars: int = 3500) -> tuple[str, bool]:
    body = str(text or "")
    if len(body) <= int(max_chars):
        return body, False
    return body[: int(max_chars)] + "\n... [trim]", True


def build_digest(
    *,
    env: str,
    title: str,
    summary_md: str = "",
    risk_events_jsonl: str = "",
    candidates_jsonl: str = "",
    acceptance_report_md: str = "",
    max_events: int = 10,
) -> dict[str, Any]:
    risk_text, severity_count = _risk_lines(risk_events_jsonl, max_events=max_events)
    counts = _candidate_counts(candidates_jsonl)
    summary_text = _load_text(summary_md)
    accept_text = _load_text(acceptance_report_md)

    msg = "\n".join(
        [
            f"# {title}",
            f"env={env}",
            "",
            "## Candidates",
            json.dumps(counts, ensure_ascii=False),
            "",
            "## Risk Events (recent)",
            risk_text or "none",
            "",
            "## Observation Summary",
            summary_text.strip() or "none",
            "",
            "## Acceptance Report",
            accept_text.strip() or "none",
        ]
    )
    msg, trim = _trim_text(msg)
    return {
        "message": msg,
        "truncated": trim,
        "severity_count": severity_count,
        "candidates_summary": counts,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build digest text from local files")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--summary-md", default="")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events.jsonl")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--acceptance-report-md", default="")
    parser.add_argument("--max-events", type=int, default=10)
    parser.add_argument("--title", default="Testnet Observation Digest")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    out = build_digest(
        env=str(args.env or "testnet"),
        title=str(args.title or "Testnet Observation Digest"),
        summary_md=str(args.summary_md or ""),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events.jsonl"),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        acceptance_report_md=str(args.acceptance_report_md or ""),
        max_events=int(args.max_events or 10),
    )
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
