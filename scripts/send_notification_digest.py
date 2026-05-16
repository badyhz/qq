from __future__ import annotations

import argparse
import json

from core.notification_sender import send_notification
from scripts.generate_notification_digest import build_digest


def run_notification_digest(
    *,
    env: str,
    channel: str,
    summary_md: str,
    risk_events_jsonl: str,
    candidates_jsonl: str,
    acceptance_report_md: str,
    dry_run: bool,
    send: bool,
    max_events: int,
    title: str,
) -> dict:
    digest = build_digest(
        env=env,
        title=title,
        summary_md=summary_md,
        risk_events_jsonl=risk_events_jsonl,
        candidates_jsonl=candidates_jsonl,
        acceptance_report_md=acceptance_report_md,
        max_events=max_events,
    )
    result = send_notification(
        env=env,
        channel=channel,
        title=title,
        message=str(digest.get("message", "")),
        dry_run=bool(dry_run),
        send=bool(send),
    )
    return {
        "env": env,
        "channel": channel,
        "dry_run": bool(dry_run),
        "send": bool(send),
        "truncated": bool(digest.get("truncated", False)),
        "severity_count": dict(digest.get("severity_count", {})),
        "candidates_summary": dict(digest.get("candidates_summary", {})),
        "notification_result": result,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send notification digest for testnet observation")
    parser.add_argument("--env", default="testnet")
    parser.add_argument("--channel", default="stdout")
    parser.add_argument("--summary-md", default="")
    parser.add_argument("--risk-events-jsonl", default="logs/risk_events.jsonl")
    parser.add_argument("--candidates-jsonl", default="logs/execution_candidates.jsonl")
    parser.add_argument("--acceptance-report-md", default="logs/testnet_acceptance_report.md")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--max-events", type=int, default=10)
    parser.add_argument("--title", default="Testnet Observation Digest")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = run_notification_digest(
        env=str(args.env or "testnet"),
        channel=str(args.channel or "stdout"),
        summary_md=str(args.summary_md or ""),
        risk_events_jsonl=str(args.risk_events_jsonl or "logs/risk_events.jsonl"),
        candidates_jsonl=str(args.candidates_jsonl or "logs/execution_candidates.jsonl"),
        acceptance_report_md=str(args.acceptance_report_md or "logs/testnet_acceptance_report.md"),
        dry_run=bool(args.dry_run),
        send=bool(args.send),
        max_events=int(args.max_events or 10),
        title=str(args.title or "Testnet Observation Digest"),
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
