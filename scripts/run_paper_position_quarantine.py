"""Phase 10G-2 Legacy Paper Position Quarantine runner.

Reads paper_positions.json, tags legacy positions for exclusion from stats.
No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.paper_trading.paper_position_quarantine import quarantine_positions

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "READONLY_METADATA_ONLY", "QUARANTINE_TAGGER",
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_input_path(date_str: str) -> str:
    return os.path.join(REPORT_DIR, f"{date_str}_paper_positions.json")


def render_markdown(result: dict) -> str:
    lines = [
        "# Legacy Paper Position Quarantine",
        "",
        f"**Date:** {result['date']}",
        f"**Source:** {result['source_file']}",
        "",
        "## Summary",
        "",
        f"- Total positions: {result['position_count']}",
        f"- Quarantined (legacy): {result['quarantined_count']}",
        f"- Clean: {result['clean_count']}",
        f"- Excluded from stats: {result['excluded_from_stats_count']}",
        "",
    ]

    reason_counts = result.get("reason_counts", {})
    if reason_counts:
        lines.extend(["## Quarantine Reasons", ""])
        for reason, count in sorted(reason_counts.items()):
            lines.append(f"- {reason}: {count}")
        lines.append("")

    clean = result.get("clean_summary", {})
    if clean:
        lines.extend(["## Clean Summary (non-excluded only)", ""])
        lines.append(f"- Clean positions: {clean.get('clean_position_count', 0)}")
        lines.append(f"- OPEN: {clean.get('clean_open_count', 0)}")
        lines.append(f"- TP: {clean.get('clean_take_profit_hit_count', 0)}")
        lines.append(f"- SL: {clean.get('clean_stop_loss_hit_count', 0)}")
        lines.append(f"- Timeout: {clean.get('clean_timeout_exit_count', 0)}")
        lines.append(f"- Excluded: {clean.get('excluded_count', 0)}")
        lines.append(f"- Legacy excluded: {clean.get('legacy_excluded_count', 0)}")
        lines.append(f"- Clean PnL: {clean.get('clean_total_realized_pnl', 0)}")
        lines.append(f"- Clean avg R: {clean.get('clean_avg_r_multiple', 0)}")
        lines.append("")

    positions = result.get("positions", [])
    quarantined = [p for p in positions if p.get("excluded_from_performance_stats")]
    clean_pos = [p for p in positions if not p.get("excluded_from_performance_stats")]

    if quarantined:
        lines.extend(["## Quarantined Positions", ""])
        for p in quarantined:
            lines.extend(_position_lines(p, quarantined=True))
            lines.append("")

    if clean_pos:
        lines.extend(["## Clean Positions", ""])
        for p in clean_pos:
            lines.extend(_position_lines(p, quarantined=False))
            lines.append("")

    lines.extend([
        "## Safety",
        "",
        "- Paper-only: YES",
        "- Shadow-only: YES",
        "- No order: YES",
        "- No account: YES",
        "- No testnet/live: YES",
        "- No secret: YES",
        "- No real execution: YES",
        "- Readonly metadata only: YES",
        "",
    ])
    return "\n".join(lines)


def _position_lines(p: dict, quarantined: bool) -> list[str]:
    tag = "LEGACY" if quarantined else "CLEAN"
    lines = [
        f"### [{tag}] {p.get('strategy_id', '')}｜{p.get('symbol', '')}｜{p.get('side', '')}",
        "",
        f"- status: {p.get('status', '')}",
        f"- entry: {p.get('entry_price', 0)}",
        f"- lifecycle_mode: {p.get('lifecycle_mode', 'N/A')}",
        f"- opened_bar_time: {p.get('opened_bar_time', 'N/A')}",
        f"- quarantine_status: {p.get('quarantine_status', '')}",
        f"- excluded_from_stats: {p.get('excluded_from_performance_stats', False)}",
    ]
    reasons = p.get("quarantine_reasons", [])
    if reasons:
        lines.append(f"- reasons: {', '.join(reasons)}")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Phase 10G-2 legacy position quarantine")
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--input-file", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=REPORT_DIR)
    args = parser.parse_args()

    date_str = args.date or _today_str()
    input_path = args.input_file or _default_input_path(date_str)

    if not os.path.isfile(input_path):
        print(f"ERROR: input file not found: {input_path}")
        return 1

    with open(input_path) as f:
        data = json.load(f)

    positions = data.get("positions", [])
    print(f"Loaded {len(positions)} positions from {input_path}")

    result = quarantine_positions(positions, date_str, source_file=input_path)
    result_dict = result.to_dict()

    os.makedirs(args.output_dir, exist_ok=True)

    # Quarantine JSON
    q_path = os.path.join(args.output_dir, f"{date_str}_paper_positions_quarantine.json")
    with open(q_path, "w") as f:
        json.dump(result_dict, f, indent=2)
    print(f"Quarantine JSON: {q_path}")

    # Quarantine Markdown
    md_path = os.path.join(args.output_dir, f"{date_str}_paper_positions_quarantine.md")
    with open(md_path, "w") as f:
        f.write(render_markdown(result_dict))
    print(f"Quarantine Markdown: {md_path}")

    # Clean summary JSON
    clean_path = os.path.join(args.output_dir, f"{date_str}_paper_positions_clean_summary.json")
    with open(clean_path, "w") as f:
        json.dump({
            "date": date_str,
            "source_file": input_path,
            "clean_summary": result_dict["clean_summary"],
            "quarantined_count": result_dict["quarantined_count"],
            "clean_count": result_dict["clean_count"],
            "reason_counts": result_dict["reason_counts"],
            "safety_flags": SAFETY_FLAGS,
            "dry_run_only": True,
            "actually_executed": False,
        }, f, indent=2)
    print(f"Clean summary: {clean_path}")

    print(f"\n=== Quarantine Complete ===")
    print(f"Total: {result_dict['position_count']}")
    print(f"Quarantined: {result_dict['quarantined_count']}")
    print(f"Clean: {result_dict['clean_count']}")
    print(f"Excluded from stats: {result_dict['excluded_from_stats_count']}")
    reasons = result_dict["reason_counts"]
    if reasons:
        print(f"Reasons: {reasons}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
