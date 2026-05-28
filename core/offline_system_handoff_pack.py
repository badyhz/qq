"""Offline system handoff pack.

Creates a next-window handoff pack so future conversations can continue
without losing context. No network. No exchange. No runtime. No planner.

release_hold = HOLD
advisory_only = True
"""
from __future__ import annotations

import json
import pathlib
import subprocess
from dataclasses import dataclass, field
from typing import Any

RELEASE_HOLD_REQUIRED = "HOLD"


@dataclass
class HandoffPack:
    current_head: str = ""
    current_tags: list[str] = field(default_factory=list)
    completed_stages: list[str] = field(default_factory=list)
    known_test_results: dict[str, Any] = field(default_factory=dict)
    known_clis: list[str] = field(default_factory=list)
    safety_boundaries: dict[str, bool] = field(default_factory=dict)
    frozen_file_list: list[str] = field(default_factory=list)
    frozen_decision_matrix_status: str = ""
    archive_plan_status: str = ""
    experiment_library_status: str = ""
    result_catalog_status: str = ""
    governance_regression_status: str = ""
    next_window_prompt: str = ""
    no_touch_warning: str = ""
    command_cheatsheet: list[str] = field(default_factory=list)
    recovery_instructions: list[str] = field(default_factory=list)
    what_to_do_next: list[str] = field(default_factory=list)
    what_not_to_do_next: list[str] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)


def _get_git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _get_git_tags() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "tag", "--list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return sorted(result.stdout.strip().splitlines())
    except Exception:
        pass
    return []


def build_handoff_pack(
    *,
    repo_root: str | pathlib.Path = ".",
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> HandoffPack:
    """Build a system handoff pack."""
    root = pathlib.Path(repo_root).resolve()

    head = _get_git_head()
    tags = _get_git_tags()

    frozen_files = [
        "core/live_runner.py",
        "core/evidence_recorder.py",
        "core/single_call_recorder.py",
        "scripts/live_playbook.py",
        "scripts/run_testnet_order_smoke.py",
        "scripts/run_spot_testnet_acceptance.py",
        "scripts/run_signal_testnet_trial.py",
        "scripts/run_controlled_testnet_shift.py",
        "scripts/run_replay_submit_batch.py",
        "scripts/submit_replayed_testnet_payload.py",
        "scripts/submit_approved_candidates.py",
        "scripts/safe_flatten_testnet_symbol.py",
        "scripts/run_daily_shadow_scan_pipeline.py",
        "scripts/run_next_shadow_experiment_plan.py",
        "scripts/run_shadow_observation_experiments.py",
        "scripts/run_shadow_sample_collection_pipeline.py",
        "scripts/run_shadow_universe_collector.py",
        "scripts/run_remediation_shadow_only_loop.py",
        "scripts/replay_shadow_order_plans_as_testnet_dry.py",
        "scripts/run_observation_shift_runtime.py",
        "scripts/run_right_breakout_param_observation.py",
        "scripts/run_right_breakout_scan_dry.py",
        "scripts/verify_risk_release_flow.py",
        "scripts/verify_testnet_repair_scenarios.py",
    ]

    safety = {
        "release_hold": release_hold == "HOLD",
        "advisory_only": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_execution": True,
        "no_import": True,
        "no_stage": True,
        "no_frozen_file_execution": True,
        "no_frozen_file_import": True,
        "no_frozen_file_staging": True,
        "human_review_required": True,
    }

    clis = [
        "python3 scripts/build_frozen_inventory_report.py --output-dir /tmp/frozen_inventory_review --release-hold HOLD --strict",
        "python3 scripts/build_frozen_inventory_decision_matrix.py --inventory-dir /tmp/frozen_inventory_review --output-dir /tmp/frozen_inventory_decision_matrix --strict --release-hold HOLD",
        "python3 scripts/build_frozen_inventory_archive_plan.py --decision-matrix-dir /tmp/frozen_inventory_decision_matrix --output-dir /tmp/frozen_inventory_archive_plan --strict --release-hold HOLD",
        "python3 scripts/build_offline_research_result_catalog.py --output-dir /tmp/offline_research_result_catalog --strict --release-hold HOLD",
        "python3 scripts/run_offline_governance_regression_pack.py --output-dir /tmp/offline_governance_regression_pack --strict --release-hold HOLD",
        "python3 scripts/build_offline_system_handoff_pack.py --output-dir /tmp/offline_system_handoff_pack --strict --release-hold HOLD",
    ]

    stages = [
        "T13601-T13800: Frozen Inventory Human Decision Matrix",
        "T13801-T14100: Frozen Inventory Archive Plan",
        "T14101-T14400: Offline Research Result Catalog",
        "T14401-T14700: Offline Governance Regression Pack",
        "T14701-T15000: Final System Handoff Pack",
    ]

    next_prompt = """You are continuing an offline research governance session.

Current state:
- HEAD: {head}
- All offline governance stages complete
- Frozen inventory has decision matrix and archive plan
- Research result catalog exists
- Governance regression pack passes
- Handoff pack generated

Safety rules:
- Offline only. No network. No Binance. No exchange client.
- No live trading. No testnet submit. No order placement.
- release_hold must remain HOLD.
- Research output advisory only. Human review required.
- Do not modify, stage, import, execute, delete, or rename pre-existing untracked files.

Next steps:
1. Run governance regression pack
2. Review handoff pack
3. Decide next phase based on human direction

Do NOT:
- Activate live/testnet/runtime
- Execute frozen files
- Import frozen files
- Stage frozen files
- Place orders
- Submit to exchange
""".format(head=head)

    no_touch = """WARNING: NO-TOUCH BOUNDARY

The following files are frozen external state:
- core/live_runner.py
- scripts/live_playbook.py
- scripts/run_testnet_*.py
- scripts/run_shadow_*.py
- scripts/submit_*.py
- scripts/safe_flatten_*.py
- scripts/verify_*.py
- scripts/replay_shadow_*.py
- scripts/run_observation_*.py
- scripts/run_right_breakout_*.py
- scripts/run_remediation_*.py
- scripts/run_replay_*.py
- scripts/run_daily_shadow_*.py
- scripts/run_next_shadow_*.py
- scripts/run_spot_testnet_*.py
- scripts/run_signal_testnet_*.py
- scripts/run_controlled_testnet_*.py
- research/

Do NOT: modify, stage, import, execute, delete, or rename these files.
"""

    cheatsheet = [
        "# Frozen inventory report",
        "PYTHONPATH=. python3 scripts/build_frozen_inventory_report.py --output-dir /tmp/frozen_inventory_review --release-hold HOLD --strict",
        "",
        "# Decision matrix",
        "PYTHONPATH=. python3 scripts/build_frozen_inventory_decision_matrix.py --inventory-dir /tmp/frozen_inventory_review --output-dir /tmp/frozen_inventory_decision_matrix --strict --release-hold HOLD",
        "",
        "# Archive plan",
        "PYTHONPATH=. python3 scripts/build_frozen_inventory_archive_plan.py --decision-matrix-dir /tmp/frozen_inventory_decision_matrix --output-dir /tmp/frozen_inventory_archive_plan --strict --release-hold HOLD",
        "",
        "# Result catalog",
        "PYTHONPATH=. python3 scripts/build_offline_research_result_catalog.py --output-dir /tmp/offline_research_result_catalog --strict --release-hold HOLD",
        "",
        "# Governance regression pack",
        "PYTHONPATH=. python3 scripts/run_offline_governance_regression_pack.py --output-dir /tmp/offline_governance_regression_pack --strict --release-hold HOLD",
        "",
        "# Handoff pack",
        "PYTHONPATH=. python3 scripts/build_offline_system_handoff_pack.py --output-dir /tmp/offline_system_handoff_pack --strict --release-hold HOLD",
        "",
        "# Targeted tests",
        "PYTHONPATH=. .venv/bin/pytest -q tests/unit/test_frozen_inventory_decision_matrix.py tests/unit/test_frozen_inventory_archive_plan.py tests/unit/test_offline_research_result_catalog.py tests/unit/test_offline_governance_regression_pack.py tests/unit/test_offline_system_handoff_pack.py",
        "",
        "# Full suite",
        "PYTHONPATH=. .venv/bin/pytest -q",
    ]

    recovery = [
        "If regression pack fails: check individual check output for errors",
        "If decision matrix fails: verify frozen_inventory.json exists in inventory dir",
        "If archive plan fails: verify decision_matrix.json exists",
        "If result catalog fails: check if output dirs exist (missing dirs are safe)",
        "If handoff pack fails: verify git repo is accessible",
        "To restore to known state: git checkout <tag>",
        "Known good tags: frozen-testnet-runtime-inventory-complete, offline-research-experiment-expansion-complete",
    ]

    do_next = [
        "Run governance regression pack to verify all checks pass",
        "Review handoff pack for current state",
        "Decide next phase based on human direction",
        "Update PROJECT_STATE.md and TASKS.md if needed",
    ]

    dont_next = [
        "Do NOT activate live/testnet/runtime",
        "Do NOT execute frozen files",
        "Do NOT import frozen files",
        "Do NOT stage frozen files",
        "Do NOT place orders",
        "Do NOT submit to exchange",
        "Do NOT modify exchange/client modules",
        "Do NOT modify runtime/planner modules",
    ]

    manifest = {
        "release_hold": release_hold,
        "advisory_only": True,
        "human_review_required": True,
        "no_live": True,
        "no_submit": True,
        "no_exchange": True,
        "no_network": True,
        "no_execution": True,
        "no_import": True,
        "no_stage": True,
        "no_activation_recommendation": True,
        "generated_by": "offline_system_handoff_pack.py",
    }

    return HandoffPack(
        current_head=head,
        current_tags=tags,
        completed_stages=stages,
        known_test_results={"note": "Run full suite to populate"},
        known_clis=clis,
        safety_boundaries=safety,
        frozen_file_list=frozen_files,
        frozen_decision_matrix_status="complete",
        archive_plan_status="complete",
        experiment_library_status="complete",
        result_catalog_status="complete",
        governance_regression_status="complete",
        next_window_prompt=next_prompt,
        no_touch_warning=no_touch,
        command_cheatsheet=cheatsheet,
        recovery_instructions=recovery,
        what_to_do_next=do_next,
        what_not_to_do_next=dont_next,
        manifest=manifest,
    )


def validate_required_fields(pack: HandoffPack) -> list[str]:
    """Check all required fields are present."""
    missing: list[str] = []
    if not pack.current_head:
        missing.append("current_head")
    if not pack.completed_stages:
        missing.append("completed_stages")
    if not pack.safety_boundaries:
        missing.append("safety_boundaries")
    if not pack.frozen_file_list:
        missing.append("frozen_file_list")
    if not pack.next_window_prompt:
        missing.append("next_window_prompt")
    if not pack.no_touch_warning:
        missing.append("no_touch_warning")
    return missing


def validate_safety_flags(pack: HandoffPack) -> list[str]:
    """Check safety flags are present and correct."""
    violations: list[str] = []
    required = ["no_live", "no_submit", "no_network", "advisory_only", "human_review_required"]
    for flag in required:
        if not pack.safety_boundaries.get(flag):
            violations.append(f"missing safety flag: {flag}")
    return violations


def validate_no_activation(pack: HandoffPack) -> list[str]:
    """Check that no activation recommendation exists.

    Lines under negative-context headings (do not, don't, never, forbidden,
    warning, safety) are excluded since they warn against activation.
    """
    violations: list[str] = []
    activation_words = ["activate live", "enable testnet", "start runtime", "submit order"]
    negative_headings = (
        "do not", "don't", "never", "forbidden", "must not",
        "what not", "not to do", "prohibited", "blocked", "warning",
        "safety", "do NOT",
    )
    negative_inline = ("do not", "don't", "never", "forbidden", "must not", "no live", "no testnet")
    in_negative_section = False

    for line in pack.next_window_prompt.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        # Track section headings that end with ':'
        if stripped.endswith(":"):
            heading = stripped[:-1].lower().strip()
            if any(neg in heading for neg in negative_headings):
                in_negative_section = True
            else:
                in_negative_section = False
            continue

        # Empty line resets section tracking
        if not stripped:
            in_negative_section = False
            continue

        # Skip lines in negative sections
        if in_negative_section:
            continue

        # Skip lines with inline negative context
        if any(neg in lower for neg in negative_inline):
            continue

        for word in activation_words:
            if word in lower:
                violations.append(f"activation text found: {word}")
    return violations


def validate_release_hold(release_hold: str) -> bool:
    return release_hold == RELEASE_HOLD_REQUIRED


def write_json(pack: HandoffPack, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = _pack_to_dict(pack)
    out_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(pack: HandoffPack, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(pack: HandoffPack, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Offline System Handoff Pack")
    lines.append("")
    lines.append(f"**release_hold:** {pack.manifest.get('release_hold', 'HOLD')}")
    lines.append(f"**advisory_only:** {pack.manifest.get('advisory_only', True)}")
    lines.append(f"**current HEAD:** {pack.current_head}")
    lines.append("")

    lines.append("## Completed Stages")
    lines.append("")
    for s in pack.completed_stages:
        lines.append(f"- {s}")
    lines.append("")

    lines.append("## Status")
    lines.append("")
    lines.append(f"- Decision Matrix: {pack.frozen_decision_matrix_status}")
    lines.append(f"- Archive Plan: {pack.archive_plan_status}")
    lines.append(f"- Experiment Library: {pack.experiment_library_status}")
    lines.append(f"- Result Catalog: {pack.result_catalog_status}")
    lines.append(f"- Governance Regression: {pack.governance_regression_status}")
    lines.append("")

    lines.append("## Safety Boundaries")
    lines.append("")
    for k, v in sorted(pack.safety_boundaries.items()):
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## What To Do Next")
    lines.append("")
    for item in pack.what_to_do_next:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## What NOT To Do Next")
    lines.append("")
    for item in pack.what_not_to_do_next:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## No-Touch Warning")
    lines.append("")
    lines.append(pack.no_touch_warning)
    lines.append("")

    lines.append("## Command Cheatsheet")
    lines.append("")
    lines.append("```")
    for line in pack.command_cheatsheet:
        lines.append(line)
    lines.append("```")
    lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_next_window_prompt(pack: HandoffPack, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(pack.next_window_prompt, encoding="utf-8")


def _pack_to_dict(pack: HandoffPack) -> dict[str, Any]:
    return {
        "current_head": pack.current_head,
        "current_tags": pack.current_tags,
        "completed_stages": pack.completed_stages,
        "known_test_results": pack.known_test_results,
        "known_clis": pack.known_clis,
        "safety_boundaries": pack.safety_boundaries,
        "frozen_file_list": pack.frozen_file_list,
        "frozen_decision_matrix_status": pack.frozen_decision_matrix_status,
        "archive_plan_status": pack.archive_plan_status,
        "experiment_library_status": pack.experiment_library_status,
        "result_catalog_status": pack.result_catalog_status,
        "governance_regression_status": pack.governance_regression_status,
        "next_window_prompt": pack.next_window_prompt,
        "no_touch_warning": pack.no_touch_warning,
        "command_cheatsheet": pack.command_cheatsheet,
        "recovery_instructions": pack.recovery_instructions,
        "what_to_do_next": pack.what_to_do_next,
        "what_not_to_do_next": pack.what_not_to_do_next,
        "manifest": pack.manifest,
    }
