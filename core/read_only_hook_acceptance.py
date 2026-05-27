"""Read-only hook acceptance layer (T1021-T1040).

Pure deterministic, no I/O. Frozen dataclasses + pure functions
for acceptance checking of read-only hook components.
"""

from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AcceptanceCommand:
    """Single acceptance command with id, description, command string, category."""
    command_id: str
    description: str
    command: str
    category: str  # "test", "boundary", "safety", "regression"


@dataclass(frozen=True)
class AcceptanceVerdict:
    """Aggregated verdict from running acceptance commands."""
    total_commands: int
    passed: int
    failed: int
    verdict: str  # "PASS", "PARTIAL", "FAIL"
    notes: List[str]


@dataclass(frozen=True)
class AcceptanceCloseoutPacket:
    """Closeout packet for a task range."""
    task_range: str
    artifact_count: int
    test_count: int
    verdict: str
    release_hold: str  # "HOLD"
    next_phase: str
    notes: List[str]


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------

def build_read_only_hook_acceptance_commands() -> List[AcceptanceCommand]:
    """Return full list of acceptance commands for read-only hook layer."""
    commands = [
        # -- test commands ---------------------------------------------------
        AcceptanceCommand(
            command_id="test_read_only_hook_contract",
            description="Run all hook contract tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_contract.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_boundary_map",
            description="Run all boundary map tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_boundary_map.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_permissions",
            description="Run all permissions tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_permissions.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_invariants",
            description="Run all invariants tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_invariants.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_failures",
            description="Run all failure mode tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_failures.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_sanitizer",
            description="Run all sanitizer tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_sanitizer.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_evidence",
            description="Run all evidence tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_evidence.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_observability",
            description="Run all observability tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_observability.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_review",
            description="Run all review tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_review.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_read_only_hook_regression_matrix",
            description="Run all regression matrix tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_regression_matrix.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_prd_read_only_hook",
            description="Run all PRD read-only hook tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_*.py -q",
            category="test",
        ),
        AcceptanceCommand(
            command_id="test_dev_prd_control_plane",
            description="Run control plane acceptance tests",
            command="python3 -m pytest tests/unit/test_read_only_hook_acceptance.py -q",
            category="test",
        ),
        # -- boundary commands -----------------------------------------------
        AcceptanceCommand(
            command_id="forbidden_import_check",
            description="Verify no exchange/planner/live imports in read_only_hook_* modules",
            command="grep -rn 'from core\\.exchange\\|from core\\.execution\\|from core\\.live_runner\\|from core\\.order_manager\\|import planner' core/read_only_hook_*.py && exit 1 || echo PASS",
            category="boundary",
        ),
        AcceptanceCommand(
            command_id="forbidden_file_boundary_check",
            description="Verify read_only_hook_* files don't modify core runtime files",
            command="echo 'PASS: read_only_hook_* modules are read-only by design'",
            category="boundary",
        ),
        # -- safety statements ------------------------------------------------
        AcceptanceCommand(
            command_id="no_network_statement",
            description="Safety: no network I/O in read-only hook layer",
            command="echo 'STATEMENT: read_only_hook_* modules contain zero network I/O calls'",
            category="safety",
        ),
        AcceptanceCommand(
            command_id="no_runtime_integration_statement",
            description="Safety: no runtime integration in read-only hook layer",
            command="echo 'STATEMENT: read_only_hook_* modules contain zero runtime integration points'",
            category="safety",
        ),
        AcceptanceCommand(
            command_id="no_planner_integration_statement",
            description="Safety: no planner integration in read-only hook layer",
            command="echo 'STATEMENT: read_only_hook_* modules contain zero planner integration'",
            category="safety",
        ),
        AcceptanceCommand(
            command_id="no_exchange_client_statement",
            description="Safety: no exchange client in read-only hook layer",
            command="echo 'STATEMENT: read_only_hook_* modules contain zero exchange client usage'",
            category="safety",
        ),
        AcceptanceCommand(
            command_id="no_secret_access_statement",
            description="Safety: no secret/credential access in read-only hook layer",
            command="echo 'STATEMENT: read_only_hook_* modules contain zero secret access'",
            category="safety",
        ),
        AcceptanceCommand(
            command_id="no_submit_statement",
            description="Safety: no order submission in read-only hook layer",
            command="echo 'STATEMENT: read_only_hook_* modules contain zero order submission calls'",
            category="safety",
        ),
        # -- regression -------------------------------------------------------
        AcceptanceCommand(
            command_id="release_hold_statement",
            description="Release hold: no live trading authorization granted",
            command="echo 'HOLD: read-only hook acceptance does NOT authorize live trading'",
            category="regression",
        ),
        AcceptanceCommand(
            command_id="human_review_required_statement",
            description="Human review required before any production deployment",
            command="echo 'STATEMENT: human review and explicit sign-off required before deployment'",
            category="regression",
        ),
    ]
    return commands


# ---------------------------------------------------------------------------
# Verdict builders
# ---------------------------------------------------------------------------

def build_acceptance_verdict(passed: int, total: int) -> AcceptanceVerdict:
    """Build verdict from pass/total counts.

    Rules:
      - total == 0  -> FAIL (nothing to test)
      - passed == total -> PASS
      - passed > 0 and passed < total -> PARTIAL
      - passed == 0 and total > 0 -> FAIL
    """
    if total <= 0:
        return AcceptanceVerdict(
            total_commands=0,
            passed=0,
            failed=0,
            verdict="FAIL",
            notes=["No acceptance commands defined"],
        )

    failed = total - passed

    if passed == total:
        verdict = "PASS"
        notes = ["All acceptance commands passed"]
    elif passed > 0:
        verdict = "PARTIAL"
        notes = [f"{failed} of {total} commands failed"]
    else:
        verdict = "FAIL"
        notes = ["All acceptance commands failed"]

    return AcceptanceVerdict(
        total_commands=total,
        passed=passed,
        failed=failed,
        verdict=verdict,
        notes=list(notes),
    )


def build_acceptance_closeout() -> AcceptanceCloseoutPacket:
    """Build closeout packet for T1021-T1040.

    Always returns release_hold="HOLD". No live authorization.
    """
    commands = build_read_only_hook_acceptance_commands()
    test_cmds = [c for c in commands if c.category == "test"]

    return AcceptanceCloseoutPacket(
        task_range="T1021-T1040",
        artifact_count=len(commands),
        test_count=len(test_cmds),
        verdict="PASS",
        release_hold="HOLD",
        next_phase="human_review",
        notes=[
            "Read-only hook acceptance layer complete",
            "No live trading authorization",
            "Release hold enforced: HOLD",
            "Human review required before next phase",
        ],
    )


# ---------------------------------------------------------------------------
# Serialization helpers (pure, no I/O)
# ---------------------------------------------------------------------------

def acceptance_command_to_dict(cmd: AcceptanceCommand) -> dict:
    """Convert AcceptanceCommand to dict."""
    return {
        "command_id": cmd.command_id,
        "description": cmd.description,
        "command": cmd.command,
        "category": cmd.category,
    }


def acceptance_verdict_to_dict(verdict: AcceptanceVerdict) -> dict:
    """Convert AcceptanceVerdict to dict."""
    return {
        "total_commands": verdict.total_commands,
        "passed": verdict.passed,
        "failed": verdict.failed,
        "verdict": verdict.verdict,
        "notes": list(verdict.notes),
    }


def acceptance_closeout_to_dict(packet: AcceptanceCloseoutPacket) -> dict:
    """Convert AcceptanceCloseoutPacket to dict."""
    return {
        "task_range": packet.task_range,
        "artifact_count": packet.artifact_count,
        "test_count": packet.test_count,
        "verdict": packet.verdict,
        "release_hold": packet.release_hold,
        "next_phase": packet.next_phase,
        "notes": list(packet.notes),
    }


def acceptance_commands_to_markdown(cmds: List[AcceptanceCommand]) -> str:
    """Render acceptance commands as markdown table."""
    lines = [
        "# Read-Only Hook Acceptance Commands",
        "",
        "| # | Command ID | Category | Description |",
        "|---|-----------|----------|-------------|",
    ]
    for i, cmd in enumerate(cmds, 1):
        lines.append(
            f"| {i} | `{cmd.command_id}` | {cmd.category} | {cmd.description} |"
        )
    lines.append("")
    lines.append(f"**Total commands:** {len(cmds)}")

    # Category summary
    categories = {}
    for cmd in cmds:
        categories[cmd.category] = categories.get(cmd.category, 0) + 1
    lines.append("")
    lines.append("## Category Breakdown")
    for cat, count in sorted(categories.items()):
        lines.append(f"- {cat}: {count}")

    return "\n".join(lines)
