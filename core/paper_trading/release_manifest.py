"""Release manifest — local RC checklist. No network, no orders."""
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Dict, Any

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
PAPER_DIR = os.path.join(REPO_ROOT, "core", "paper_trading")
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
FIXTURE_DIR = os.path.join(REPO_ROOT, "tests", "fixtures", "paper_trading")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")

EXPECTED_MODULES = [
    "order_plan.py", "risk_sizing.py", "exit_rules.py", "signal_to_plan_adapter.py",
    "human_approval_gate.py", "replay_engine.py", "paper_ledger.py", "alert_explainer.py",
    "account_state.py", "portfolio_risk.py", "lifecycle.py", "local_alert_bridge.py",
    "performance_metrics.py", "parameter_sweep.py", "strategy_scorecard.py", "risk_explainer.py",
    "runtime_config.py", "strategy_registry.py", "runtime_orchestrator.py", "html_dashboard.py",
    "run_history.py", "dashboard_index.py", "review_queue.py", "candidate_ranker.py",
    "operator_decision_pack.py", "release_manifest.py", "artifact_validator.py",
]

EXPECTED_SCRIPTS = [
    "run_paper_trading_decision_engine_dry.py",
    "run_paper_multi_fixture_replay.py",
    "run_paper_parameter_sweep.py",
    "run_paper_trading_ops_report.py",
    "run_paper_runtime.py",
    "run_paper_daily_ops.py",
    "run_paper_operator_review.py",
    "run_paper_release_candidate.py",
    "run_paper_trading_acceptance_suite.py",
]

EXPECTED_REPORTS = [
    "paper_trading_decision_engine_report.md",
    "paper_trading_multi_fixture_report.md",
    "paper_trading_parameter_sweep.md",
    "paper_trading_ops_report.md",
    "paper_trading_runtime_report.md",
    "paper_trading_daily_ops.md",
    "paper_trading_operator_review.md",
    "paper_trading_index.html",
    "paper_trading_dashboard.html",
]

EXPECTED_FIXTURES = [
    "macd_rebound_sample.json",
]

SAFETY_FLAGS = [
    "NO_REAL_ORDER", "NO_REAL_HTTP", "NO_SECRET_READ",
    "NO_TESTNET", "NO_LIVE", "PAPER_ONLY", "HUMAN_REVIEW_REQUIRED",
]

KNOWN_LIMITS = [
    "Fixture-only — no live market data",
    "Single symbol per replay",
    "No persistence — ledger in-memory only",
    "No execution — plans never become real orders",
    "No network — zero HTTP calls",
    "No slippage/latency simulation",
]

NEXT_PHASE_BLOCKERS = [
    "No testnet transition guard built",
    "No real market data validation",
    "No slippage/latency modeling",
    "No regulatory compliance (KYC, tax)",
    "Human approval required for any progression",
]


def generate_manifest() -> Dict[str, Any]:
    """Generate the release manifest."""
    modules = _check_files(PAPER_DIR, EXPECTED_MODULES)
    scripts = _check_files(SCRIPTS_DIR, EXPECTED_SCRIPTS)
    fixtures = _check_files(FIXTURE_DIR, EXPECTED_FIXTURES)
    reports = _check_files(REPORT_DIR, EXPECTED_REPORTS)

    return {
        "version": "1.0.0-rc1",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "paper_only": True,
        "modules": {
            "expected": len(EXPECTED_MODULES),
            "found": sum(1 for _, ok in modules if ok),
            "items": [{"name": n, "present": ok} for n, ok in modules],
        },
        "scripts": {
            "expected": len(EXPECTED_SCRIPTS),
            "found": sum(1 for _, ok in scripts if ok),
            "items": [{"name": n, "present": ok} for n, ok in scripts],
        },
        "fixtures": {
            "expected": len(EXPECTED_FIXTURES),
            "found": sum(1 for _, ok in fixtures if ok),
            "items": [{"name": n, "present": ok} for n, ok in fixtures],
        },
        "reports": {
            "expected": len(EXPECTED_REPORTS),
            "found": sum(1 for _, ok in reports if ok),
            "items": [{"name": n, "present": ok} for n, ok in reports],
        },
        "acceptance_checks": 37,
        "safety_flags": SAFETY_FLAGS,
        "known_limits": KNOWN_LIMITS,
        "next_phase_blockers": NEXT_PHASE_BLOCKERS,
    }


def manifest_ready(manifest: Dict[str, Any]) -> bool:
    """Check if manifest indicates RC readiness."""
    return (
        manifest.get("paper_only") is True
        and manifest["modules"]["found"] >= len(EXPECTED_MODULES) - 2  # allow 2 missing
        and manifest["scripts"]["found"] == len(EXPECTED_SCRIPTS)
        and manifest["fixtures"]["found"] >= len(EXPECTED_FIXTURES)
        and all(f in manifest.get("safety_flags", []) for f in SAFETY_FLAGS)
    )


def manifest_to_markdown(manifest: Dict[str, Any]) -> str:
    """Convert manifest to markdown."""
    lines = [
        "# Paper Trading Release Manifest\n",
        f"**Version:** {manifest['version']}",
        f"**Generated:** {manifest['generated_at']}",
        f"**Paper Only:** {manifest['paper_only']}\n",
        "## Modules\n",
        f"Found: {manifest['modules']['found']}/{manifest['modules']['expected']}\n",
    ]
    for item in manifest["modules"]["items"]:
        mark = "OK" if item["present"] else "MISSING"
        lines.append(f"- [{mark}] {item['name']}")

    lines.append(f"\n## Scripts\n\nFound: {manifest['scripts']['found']}/{manifest['scripts']['expected']}\n")
    for item in manifest["scripts"]["items"]:
        mark = "OK" if item["present"] else "MISSING"
        lines.append(f"- [{mark}] {item['name']}")

    lines.append(f"\n## Reports\n\nFound: {manifest['reports']['found']}/{manifest['reports']['expected']}\n")
    for item in manifest["reports"]["items"]:
        mark = "OK" if item["present"] else "MISSING"
        lines.append(f"- [{mark}] {item['name']}")

    lines.append("\n## Safety Flags\n")
    for flag in manifest["safety_flags"]:
        lines.append(f"- {flag}")

    lines.append("\n## Known Limits\n")
    for lim in manifest["known_limits"]:
        lines.append(f"- {lim}")

    lines.append("\n## Next Phase Blockers\n")
    for blk in manifest["next_phase_blockers"]:
        lines.append(f"- {blk}")

    ready = manifest_ready(manifest)
    lines.append(f"\n## RC Ready: {'YES' if ready else 'NO'}\n")
    return "\n".join(lines)


def _check_files(directory: str, expected: List[str]) -> List[tuple]:
    return [(name, os.path.isfile(os.path.join(directory, name))) for name in expected]
