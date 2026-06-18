"""Shadow Operator Status — prints current system status from latest reports.

Reads:
  - reports/strategies/*_shadow_sample_gate.json
  - reports/strategies/*_paper_performance_scorecard.json
  - reports/strategies/*_paper_positions_quarantine.json

Prints human-readable status summary with next-action guidance.
No network, no orders, no accounts, no secrets.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DEFAULT_REPORT_DIR = os.path.join(REPO_ROOT, "reports", "strategies")

SAFETY_FLAGS = [
    "PAPER_ONLY", "SHADOW_ONLY", "NO_SECRET", "NO_ENV_READ",
    "NO_ACCOUNT", "NO_ORDER", "NO_REAL_ORDER", "NO_TESTNET", "NO_LIVE",
    "NO_WEBSOCKET", "NO_PRIVATE_ENDPOINT", "NO_WEBHOOK_SEND",
    "STATUS_READ_ONLY", "NO_NETWORK",
]


def _find_latest(pattern: str) -> str | None:
    """Find the most recent file matching glob pattern."""
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def _load_json(path: str) -> dict | None:
    """Load JSON file, return None on failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def load_status(report_dir: str, date_str: str | None = None) -> dict:
    """Load status from report files."""
    status: dict = {}

    # Sample gate
    if date_str:
        gate_path = os.path.join(report_dir, f"{date_str}_shadow_sample_gate.json")
    else:
        gate_path = _find_latest(os.path.join(report_dir, "*_shadow_sample_gate.json"))
    if gate_path and os.path.isfile(gate_path):
        gate = _load_json(gate_path)
        if gate:
            status["sample_status"] = gate.get("sample_status", "UNKNOWN")
            status["testnet_gate_status"] = gate.get("testnet_gate_status", "UNKNOWN")
            status["gate_reasons"] = gate.get("gate_reasons", [])
            status["gate_file"] = gate_path

    # Scorecard
    if date_str:
        sc_path = os.path.join(report_dir, f"{date_str}_paper_performance_scorecard.json")
    else:
        sc_path = _find_latest(os.path.join(report_dir, "*_paper_performance_scorecard.json"))
    if sc_path and os.path.isfile(sc_path):
        sc = _load_json(sc_path)
        if sc:
            gm = sc.get("global_metrics", {})
            status["clean_positions"] = gm.get("clean_positions", 0)
            status["closed_clean_positions"] = gm.get("closed_positions", 0)
            status["excluded_positions"] = gm.get("excluded_positions", 0)
            status["open_positions"] = gm.get("open_positions", 0)
            status["win_rate"] = gm.get("win_rate", 0.0)
            status["profit_factor"] = gm.get("profit_factor", 0.0)
            status["avg_r_multiple"] = gm.get("avg_r_multiple", 0.0)
            status["scorecard_file"] = sc_path

    # Quarantine
    if date_str:
        q_path = os.path.join(report_dir, f"{date_str}_paper_positions_quarantine.json")
    else:
        q_path = _find_latest(os.path.join(report_dir, "*_paper_positions_quarantine.json"))
    if q_path and os.path.isfile(q_path):
        q = _load_json(q_path)
        if q:
            status["quarantined_count"] = q.get("quarantined_count", 0)
            status["clean_count"] = q.get("clean_count", 0)

    return status


def render_status(status: dict) -> str:
    """Render human-readable status text."""
    lines = [
        "Shadow Operator Status",
        "=" * 40,
        "",
    ]

    sample = status.get("sample_status", "UNKNOWN")
    gate = status.get("testnet_gate_status", "UNKNOWN")
    clean = status.get("clean_positions", "N/A")
    closed = status.get("closed_clean_positions", "N/A")
    excluded = status.get("excluded_positions", "N/A")
    open_pos = status.get("open_positions", "N/A")
    win_rate = status.get("win_rate", 0.0)
    pf = status.get("profit_factor", 0.0)
    avg_r = status.get("avg_r_multiple", 0.0)
    quarantined = status.get("quarantined_count", "N/A")

    lines.extend([
        f"sample_status: {sample}",
        f"testnet_gate_status: {gate}",
        "",
        f"clean_positions: {clean}",
        f"closed_clean_positions: {closed}",
        f"excluded_positions: {excluded}",
        f"open_positions: {open_pos}",
        f"quarantined_count: {quarantined}",
        "",
    ])

    if isinstance(closed, int) and closed > 0:
        lines.extend([
            f"win_rate: {win_rate:.2%}",
            f"profit_factor: {pf:.2f}",
            f"avg_r_multiple: {avg_r:.2f}",
            "",
        ])

    # Gate reasons
    reasons = status.get("gate_reasons", [])
    if reasons:
        lines.append("Gate reasons:")
        for r in reasons:
            lines.append(f"  - {r}")
        lines.append("")

    # Next action
    lines.extend(["=" * 40, "", "Next action:", ""])

    if sample == "INSUFFICIENT_CLOSED_SAMPLE" or gate == "BLOCKED_INSUFFICIENT_CLOSED_SAMPLE":
        lines.extend([
            "继续 shadow collection。",
            "不要 testnet。",
            "不要 live。",
            "",
            f"closed_clean_positions={closed}，不足 10，样本不够判断策略。",
        ])
    elif sample == "LOW_SAMPLE_SIZE" or gate == "BLOCKED_LOW_SAMPLE_SIZE":
        lines.extend([
            "继续 shadow collection。",
            "不要 testnet。",
            "不要 live。",
            "",
            f"closed_clean_positions={closed}，不足 30，样本偏少。",
        ])
    elif gate == "PAPER_SAMPLE_READY_FOR_HUMAN_REVIEW":
        lines.extend([
            "样本已达到人工审查门槛。",
            "请人工审查策略表现后决定下一步。",
            "系统不会自动进入 testnet 或 live。",
        ])
    else:
        lines.extend([
            "继续 shadow collection。",
            "不要 testnet。",
            "不要 live。",
        ])

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Print shadow operator status from latest reports",
    )
    parser.add_argument("--report-dir", type=str, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    if not os.path.isdir(args.report_dir):
        print(f"Report directory not found: {args.report_dir}")
        print("No reports yet. Run shadow lifecycle first.")
        return 0

    status = load_status(args.report_dir, args.date)
    if not status:
        print("No status files found.")
        print("Run shadow lifecycle or update-only pipeline first.")
        return 0

    print(render_status(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
