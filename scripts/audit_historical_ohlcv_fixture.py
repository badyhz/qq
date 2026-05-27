#!/usr/bin/env python3
"""Audit historical OHLCV CSV fixture for data quality.

Reads CSV in chunks, produces quality report in JSON and/or MD.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.historical_ohlcv_chunked_reader import summarize_dataset
from core.historical_ohlcv_schema import OHLCVColumnMapping


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Audit historical OHLCV CSV for data quality.",
    )
    p.add_argument("--input-csv", required=True, help="Path to input CSV")
    p.add_argument("--symbol", default="", help="Symbol label")
    p.add_argument("--timeframe", default="", help="Timeframe label")
    p.add_argument("--output-json", default="", help="Write JSON report to this path")
    p.add_argument("--output-md", default="", help="Write Markdown report to this path")
    p.add_argument("--chunk-size", type=int, default=500, help="Rows per chunk")
    p.add_argument(
        "--expected-interval-seconds", type=float, default=300.0,
        help="Expected bar interval in seconds",
    )
    return p


def _report_to_dict(report) -> dict:
    """Convert a HistoricalDataQualityReport to a JSON-serialisable dict."""
    return {
        "symbol": report.symbol,
        "timeframe": report.timeframe,
        "total_rows": report.total_rows,
        "valid_rows": report.valid_rows,
        "duplicate_count": report.duplicate_count,
        "gap_count": report.gap_count,
        "invalid_ohlcv_count": report.invalid_ohlcv_count,
        "is_clean": report.is_clean,
        "issue_count": len(report.issues),
        "issues": [
            {
                "issue_type": i.issue_type.value,
                "severity": i.severity.value,
                "timestamp": i.timestamp,
                "detail": i.detail,
            }
            for i in report.issues
        ],
    }


def _report_to_md(report) -> str:
    """Render a Markdown quality report."""
    lines = [
        f"# OHLCV Quality Report: {report.symbol} {report.timeframe}",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total rows | {report.total_rows} |",
        f"| Valid rows | {report.valid_rows} |",
        f"| Duplicates | {report.duplicate_count} |",
        f"| Gaps | {report.gap_count} |",
        f"| Invalid OHLCV | {report.invalid_ohlcv_count} |",
        f"| Clean | {'YES' if report.is_clean else 'NO'} |",
        "",
    ]
    if report.issues:
        lines.append("## Issues")
        lines.append("")
        lines.append("| Type | Severity | Timestamp | Detail |")
        lines.append("|------|----------|-----------|--------|")
        for issue in report.issues:
            lines.append(
                f"| {issue.issue_type.value} | {issue.severity.value} "
                f"| {issue.timestamp} | {issue.detail} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    csv_path = Path(args.input_csv)
    if not csv_path.exists():
        print(f"ERROR: file not found: {csv_path}", file=sys.stderr)
        return 1

    mapping = OHLCVColumnMapping(
        timestamp_col="timestamp", open_col="open", high_col="high",
        low_col="low", close_col="close", volume_col="volume",
    )

    report = summarize_dataset(
        csv_path=csv_path,
        column_mapping=mapping,
        chunk_size=args.chunk_size,
        symbol=args.symbol,
        timeframe=args.timeframe,
        expected_interval_seconds=args.expected_interval_seconds,
    )

    # JSON output
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(_report_to_dict(report), indent=2))
        print(f"JSON report written to {out}")

    # MD output
    if args.output_md:
        out = Path(args.output_md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_report_to_md(report))
        print(f"MD report written to {out}")

    # Summary to stdout
    print(f"Symbol: {report.symbol}  Timeframe: {report.timeframe}")
    print(f"Rows: {report.total_rows}  Valid: {report.valid_rows}  "
          f"Dup: {report.duplicate_count}  Gaps: {report.gap_count}  "
          f"Invalid: {report.invalid_ohlcv_count}")
    print(f"Clean: {'YES' if report.is_clean else 'NO'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
