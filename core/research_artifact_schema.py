"""Research artifact schema — expected fields for quality gate artifacts.

Offline only. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

# --- Required artifacts for quality gate browser ---
BROWSER_REQUIRED_ARTIFACTS: Tuple[str, ...] = (
    "manifest.json",
    "quality_gate_summary.json",
    "robustness_scorecard.json",
    "data_quality_deep_audit.json",
    "split_leakage_report.json",
    "oos_validation_report.json",
    "parameter_stability.json",
    "parameter_fragility_report.json",
    "parameter_sensitivity_ranking.json",
    "strategy_robustness_report.json",
    "portfolio_robustness_report.json",
    "portfolio_overlap_risk.json",
    "correlation_proxy_report.json",
    "negative_control_report.json",
    "random_strategy_baseline.json",
    "shuffled_returns_baseline.json",
    "inverted_signal_baseline.json",
    "bootstrap_report.json",
    "bootstrap_confidence_intervals.json",
    "regime_breakdown.json",
    "regime_failure_report.json",
    "report_quality_check.json",
    "promotion_gate_v2.json",
    "reproducibility_manifest.json",
    "rerun_diff_report.json",
    "artifact_index.json",
)

BROWSER_OPTIONAL_ARTIFACTS: Tuple[str, ...] = (
    "report.md",
    "report.html",
)

# --- Expected top-level keys per artifact ---
ARTIFACT_SCHEMA_KEYS: Dict[str, FrozenSet[str]] = {
    "manifest.json": frozenset({
        "release_hold", "no_live", "no_submit", "no_exchange",
        "no_runtime_integration", "no_planner_integration", "no_network",
        "advisory_only", "human_review_required",
        "strict_mode", "quality_gate_version",
    }),
    "quality_gate_summary.json": frozenset({
        "composite_score", "evidence_completeness",
        "hard_blocks", "warnings", "verdict",
    }),
    "robustness_scorecard.json": frozenset({
        "component_scores", "composite_score", "verdict",
    }),
    "negative_control_report.json": frozenset({
        "verdict", "baselines",
    }),
    "bootstrap_report.json": frozenset({
        "verdict", "hard_blocks", "warnings",
    }),
    "regime_breakdown.json": frozenset({
        "verdict",
    }),
    "portfolio_overlap_risk.json": frozenset({
        "verdict",
    }),
    "promotion_gate_v2.json": frozenset({
        "verdict", "hard_blocks", "warnings",
    }),
    "reproducibility_manifest.json": frozenset({
        "input_artifact_hashes", "output_artifact_hashes",
    }),
    "report_quality_check.json": frozenset({
        "verdict", "hard_blocks", "warnings",
    }),
}

# --- Required safety flag checks for manifest ---
MANIFEST_SAFETY_CHECKS: Dict[str, object] = {
    "release_hold": "HOLD",
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
    "no_network": True,
    "advisory_only": True,
    "human_review_required": True,
    "strict_mode": True,
}

# --- Forbidden imports for browser code ---
BROWSER_FORBIDDEN_IMPORTS: Tuple[str, ...] = (
    "binance", "ccxt", "exchange", "websocket",
    "requests", "httpx", "aiohttp", "urllib",
    "runtime", "planner",
    "live_submit", "live_trading",
    "testnet_submit", "testnet_client",
    "live_runner", "live_playbook",
)
