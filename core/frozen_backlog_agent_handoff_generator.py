"""T1891-T1900 - Frozen Backlog Agent Handoff Generator.

Pure function that produces a deterministic markdown prompt/packet for
handing off to a future agent. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from core.frozen_backlog_inventory import FrozenBacklogInventory
from core.frozen_backlog_report_summary import FrozenBacklogReportSummary


def generate_agent_handoff(
    inventory: FrozenBacklogInventory,
    summary: FrozenBacklogReportSummary,
) -> str:
    """Generate a deterministic agent handoff prompt.

    Pure function. No I/O. No timestamps. No network.

    Returns markdown string containing:
    - Allowed scope
    - Forbidden paths (all 22 frozen files listed explicitly)
    - Required tests to run before committing
    - Commit rules
    - release_hold = HOLD
    - Safety warnings
    """
    lines: list[str] = []

    # Header
    lines.append("# Frozen Backlog Agent Handoff Prompt")
    lines.append("")
    lines.append("release_hold = HOLD")
    lines.append("")

    # Allowed scope
    lines.append("## Allowed Scope")
    lines.append("")
    lines.append("You may ONLY touch files in these directories:")
    lines.append("")
    lines.append("- `core/*`")
    lines.append("- `scripts/*`")
    lines.append("- `docs/dev_prd/*`")
    lines.append("- `tests/*`")
    lines.append("")

    # Forbidden paths
    lines.append("## Forbidden Paths — Frozen Files (DO NOT MODIFY)")
    lines.append("")
    lines.append(
        "The following 22 files are frozen under release_hold=HOLD. "
        "You MUST NOT modify, delete, move, or execute any of them."
    )
    lines.append("")
    for rec in inventory.records:
        lines.append(f"- `{rec.file_path}` [{rec.risk_class}] {rec.category}")
    lines.append("")

    # Safety warnings
    lines.append("## Safety Warnings")
    lines.append("")
    lines.append("- release_hold MUST remain HOLD at all times")
    lines.append("- no_live MUST remain True")
    lines.append("- no_submit MUST remain True")
    lines.append("- no_exchange MUST remain True")
    lines.append("- no_runtime_integration MUST remain True")
    lines.append("- no_planner_integration MUST remain True")
    lines.append("- Do NOT import any frozen/live/testnet/submit/exchange modules")
    lines.append("- Do NOT make network calls or exchange calls")
    lines.append("- Do NOT place any orders")
    lines.append("")

    # Commit rules
    lines.append("## Commit Rules")
    lines.append("")
    lines.append("- Use explicit `git add <file>` only")
    lines.append("- NEVER use `git add .` or `git add -A`")
    lines.append("- Do NOT `git add` any of the 22 frozen files listed above")
    lines.append("- Commit messages: conventional format, <=50 chars subject")
    lines.append("")

    # Required tests
    lines.append("## Required Tests Before Committing")
    lines.append("")
    lines.append("Run these tests and ensure they all pass before committing:")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 -m pytest tests/unit/test_frozen_backlog_platform_audit.py -v")
    lines.append("python3 -m pytest tests/unit/test_frozen_backlog_agent_handoff.py -v")
    lines.append("python3 -m pytest tests/unit/test_frozen_backlog_report_validator.py -v")
    lines.append("python3 -m pytest tests/unit/test_frozen_backlog_snapshot.py -v")
    lines.append("python3 -m pytest tests/unit/test_frozen_backlog_inventory.py -v")
    lines.append("```")
    lines.append("")

    # Inventory summary
    lines.append("## Inventory Summary")
    lines.append("")
    lines.append(f"- Total frozen files: {inventory.total_count}")
    lines.append(f"- HIGH risk: {inventory.high_risk_count}")
    lines.append(f"- MEDIUM risk: {inventory.medium_risk_count}")
    lines.append(f"- Release hold: {summary.release_hold}")
    lines.append(f"- No live: {summary.no_live}")
    lines.append(f"- No submit: {summary.no_submit}")
    lines.append(f"- No exchange: {summary.no_exchange}")
    lines.append("")

    return "\n".join(lines)
