"""Offline governance regression pack.

Orchestrates key offline governance checks in sequence.
No network. No exchange. No runtime. No planner.
No frozen file execution. No live/testnet/runtime.

release_hold = HOLD
advisory_only = True
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

RELEASE_HOLD_REQUIRED = "HOLD"

# Check definitions: (name, script_path, description)
REGRESSION_CHECKS = [
    {
        "name": "validate_offline_research_experiment_library",
        "command": [".venv/bin/pytest", "-q", "tests/unit/test_offline_research_experiment_library.py"],
        "description": "Validate offline research experiment library tests",
        "required": True,
    },
    {
        "name": "validate_offline_research_stack_docs",
        "command": [".venv/bin/pytest", "-q", "tests/unit/test_offline_research_governance.py"],
        "description": "Validate offline research stack documentation and governance",
        "required": True,
    },
    {
        "name": "build_frozen_inventory_report",
        "command": [
            "python3", "scripts/build_frozen_inventory_report.py",
            "--output-dir", "/tmp/regression_frozen_inventory",
            "--release-hold", "HOLD", "--strict",
        ],
        "description": "Build frozen inventory report",
        "required": True,
    },
    {
        "name": "build_frozen_inventory_decision_matrix",
        "command": [
            "python3", "scripts/build_frozen_inventory_decision_matrix.py",
            "--inventory-dir", "/tmp/regression_frozen_inventory",
            "--output-dir", "/tmp/regression_decision_matrix",
            "--strict", "--release-hold", "HOLD",
        ],
        "description": "Build frozen inventory decision matrix",
        "required": True,
    },
    {
        "name": "build_frozen_inventory_archive_plan",
        "command": [
            "python3", "scripts/build_frozen_inventory_archive_plan.py",
            "--decision-matrix-dir", "/tmp/regression_decision_matrix",
            "--output-dir", "/tmp/regression_archive_plan",
            "--strict", "--release-hold", "HOLD",
        ],
        "description": "Build frozen inventory archive plan",
        "required": True,
    },
    {
        "name": "build_offline_research_result_catalog",
        "command": [
            "python3", "scripts/build_offline_research_result_catalog.py",
            "--output-dir", "/tmp/regression_result_catalog",
            "--strict", "--release-hold", "HOLD",
        ],
        "description": "Build offline research result catalog",
        "required": True,
    },
]

# Forbidden command patterns
FORBIDDEN_COMMANDS = [
    "curl", "wget", "requests", "httpx", "aiohttp",
    "binance", "exchange", "submit_order", "cancel_order",
    "flatten", "live_trading", "testnet_submit",
]


@dataclass
class CheckResult:
    name: str
    command: list[str]
    status: str  # PASS, FAIL, SKIPPED
    output_path: str = ""
    duration_seconds: float = 0.0
    safety_flags: dict[str, Any] = field(default_factory=dict)
    release_hold: str = "HOLD"
    advisory_only: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RegressionPackResult:
    checks: list[CheckResult]
    manifest: dict[str, Any]
    final_verdict: str = "PASS"


def _validate_command_safety(command: list[str]) -> list[str]:
    """Check that command doesn't contain forbidden patterns."""
    violations: list[str] = []
    cmd_str = " ".join(command).lower()
    for forbidden in FORBIDDEN_COMMANDS:
        if forbidden.lower() in cmd_str:
            violations.append(f"forbidden command pattern: {forbidden}")
    return violations


def _run_check(check_def: dict[str, Any], repo_root: pathlib.Path, timeout: int = 120) -> CheckResult:
    """Run a single regression check."""
    name = check_def["name"]
    command = check_def["command"]

    # Validate command safety
    violations = _validate_command_safety(command)
    if violations:
        return CheckResult(
            name=name,
            command=command,
            status="FAIL",
            errors=violations,
            safety_flags={"command_safety": False},
        )

    start = time.time()
    try:
        result = subprocess.run(
            command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = time.time() - start

        status = "PASS" if result.returncode == 0 else "FAIL"
        errors = []
        warnings = []

        if result.returncode != 0:
            errors.append(f"exit code: {result.returncode}")
            if result.stderr:
                # Truncate stderr for safety
                errors.append(f"stderr: {result.stderr[:500]}")

        return CheckResult(
            name=name,
            command=command,
            status=status,
            duration_seconds=round(duration, 2),
            safety_flags={
                "command_safety": True,
                "no_shell_true": True,
                "no_network": True,
            },
            release_hold="HOLD",
            advisory_only=True,
            errors=errors,
            warnings=warnings,
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        return CheckResult(
            name=name,
            command=command,
            status="FAIL",
            duration_seconds=round(duration, 2),
            errors=["timeout"],
            safety_flags={"command_safety": True},
        )
    except Exception as e:
        duration = time.time() - start
        return CheckResult(
            name=name,
            command=command,
            status="FAIL",
            duration_seconds=round(duration, 2),
            errors=[str(e)[:200]],
            safety_flags={"command_safety": True},
        )


def run_regression_pack(
    *,
    repo_root: str | pathlib.Path = ".",
    release_hold: str = RELEASE_HOLD_REQUIRED,
    timeout: int = 120,
) -> RegressionPackResult:
    """Run all regression checks."""
    root = pathlib.Path(repo_root).resolve()
    checks: list[CheckResult] = []

    for check_def in REGRESSION_CHECKS:
        result = _run_check(check_def, root, timeout=timeout)
        checks.append(result)

    # Determine final verdict
    failed_required = [
        c for c in checks
        if c.status == "FAIL" and any(
            d["name"] == c.name and d.get("required", True)
            for d in REGRESSION_CHECKS
        )
    ]
    final_verdict = "FAIL" if failed_required else "PASS"

    manifest = _build_manifest(checks, release_hold, final_verdict)
    return RegressionPackResult(checks=checks, manifest=manifest, final_verdict=final_verdict)


def _build_manifest(checks: list[CheckResult], release_hold: str, verdict: str) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for c in checks:
        status_counts[c.status] = status_counts.get(c.status, 0) + 1

    return {
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_execution": True,
        "no_import": True,
        "no_frozen_file_execution": True,
        "generated_by": "offline_governance_regression_pack.py",
        "total_checks": len(checks),
        "status_counts": status_counts,
        "final_verdict": verdict,
    }


def validate_release_hold(release_hold: str) -> bool:
    return release_hold == RELEASE_HOLD_REQUIRED


def write_json(pack: RegressionPackResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "manifest": pack.manifest,
        "final_verdict": pack.final_verdict,
        "checks": [_check_to_dict(c) for c in pack.checks],
    }
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(pack: RegressionPackResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(pack: RegressionPackResult, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Offline Governance Regression Pack")
    lines.append("")
    lines.append(f"**release_hold:** {pack.manifest['release_hold']}")
    lines.append(f"**advisory_only:** {pack.manifest['advisory_only']}")
    lines.append(f"**final_verdict:** {pack.final_verdict}")
    lines.append(f"**total checks:** {len(pack.checks)}")
    lines.append("")

    lines.append("## Check Results")
    lines.append("")
    lines.append("| Check | Status | Duration | Errors |")
    lines.append("|-------|--------|----------|--------|")
    for c in pack.checks:
        errs = "; ".join(c.errors) if c.errors else "none"
        lines.append(f"| {c.name} | {c.status} | {c.duration_seconds}s | {errs} |")
    lines.append("")

    lines.append("## Safety Boundary")
    lines.append("")
    lines.append("- No shell=True")
    lines.append("- No network commands")
    lines.append("- No frozen file execution")
    lines.append("- release_hold = HOLD")
    lines.append("- Advisory only. Human review required.")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _check_to_dict(check: CheckResult) -> dict[str, Any]:
    return {
        "name": check.name,
        "command": check.command,
        "status": check.status,
        "output_path": check.output_path,
        "duration_seconds": check.duration_seconds,
        "safety_flags": check.safety_flags,
        "release_hold": check.release_hold,
        "advisory_only": check.advisory_only,
        "errors": check.errors,
        "warnings": check.warnings,
    }
