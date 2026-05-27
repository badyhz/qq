"""Research quality manifest — artifact naming registry and inventory.

Enumerates all required quality gate artifacts.
Deterministic ordering. No network, no exchange.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import (
    QUALITY_GATE_GENERATED_BY,
    QUALITY_GATE_VERSION,
    RELEASE_HOLD_VALUE,
    SAFETY_FLAGS,
)


# --- Required artifact inventory ---
REQUIRED_ARTIFACTS: Tuple[str, ...] = (
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
    "report.md",
    "report.html",
    "manifest.json",
)


@dataclass(frozen=True)
class QualityManifest:
    """Quality gate manifest with safety flags and artifact hashes."""
    release_hold: str
    no_live: bool
    no_submit: bool
    no_exchange: bool
    no_runtime_integration: bool
    no_planner_integration: bool
    no_network: bool
    advisory_only: bool
    human_review_required: bool
    deterministic_seed: int
    quality_gate_version: str
    strict_mode: bool
    generated_by: str
    generated_at: str
    artifacts: Tuple[str, ...]
    input_artifact_hashes: Dict[str, str]
    output_artifact_hashes: Dict[str, str]


def build_quality_manifest(
    output_dir: Path,
    seed: int,
    strict: bool = True,
    input_hashes: Dict[str, str] = None,
    generated_at: str = None,
) -> QualityManifest:
    """Build quality manifest from output directory."""
    out_hashes = {}
    artifacts = []
    for name in sorted(REQUIRED_ARTIFACTS):
        p = output_dir / name
        if p.exists():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            out_hashes[name] = h
            artifacts.append(name)

    return QualityManifest(
        release_hold=RELEASE_HOLD_VALUE,
        no_live=SAFETY_FLAGS["no_live"],
        no_submit=SAFETY_FLAGS["no_submit"],
        no_exchange=SAFETY_FLAGS["no_exchange"],
        no_runtime_integration=SAFETY_FLAGS["no_runtime_integration"],
        no_planner_integration=SAFETY_FLAGS["no_planner_integration"],
        no_network=SAFETY_FLAGS["no_network"],
        advisory_only=True,
        human_review_required=True,
        deterministic_seed=seed,
        quality_gate_version=QUALITY_GATE_VERSION,
        strict_mode=strict,
        generated_by=QUALITY_GATE_GENERATED_BY,
        generated_at=generated_at or f"seed_{seed}",
        artifacts=tuple(sorted(artifacts)),
        input_artifact_hashes=input_hashes or {},
        output_artifact_hashes=out_hashes,
    )


def manifest_to_dict(m: QualityManifest) -> Dict[str, Any]:
    return {
        "release_hold": m.release_hold,
        "no_live": m.no_live,
        "no_submit": m.no_submit,
        "no_exchange": m.no_exchange,
        "no_runtime_integration": m.no_runtime_integration,
        "no_planner_integration": m.no_planner_integration,
        "no_network": m.no_network,
        "advisory_only": m.advisory_only,
        "human_review_required": m.human_review_required,
        "deterministic_seed": m.deterministic_seed,
        "quality_gate_version": m.quality_gate_version,
        "strict_mode": m.strict_mode,
        "generated_by": m.generated_by,
        "generated_at": m.generated_at,
        "artifacts": list(m.artifacts),
        "input_artifact_hashes": m.input_artifact_hashes,
        "output_artifact_hashes": m.output_artifact_hashes,
    }


def manifest_to_json(m: QualityManifest) -> str:
    return json.dumps(manifest_to_dict(m), sort_keys=True, indent=2)


def validate_quality_manifest(m: QualityManifest) -> List[str]:
    """Validate manifest safety flags. Returns list of errors."""
    errors = []
    if m.release_hold != RELEASE_HOLD_VALUE:
        errors.append(f"release_hold={m.release_hold}, expected HOLD")
    if not m.advisory_only:
        errors.append("advisory_only must be True")
    if not m.human_review_required:
        errors.append("human_review_required must be True")
    if not m.no_live:
        errors.append("no_live must be True")
    if not m.no_submit:
        errors.append("no_submit must be True")
    if not m.no_exchange:
        errors.append("no_exchange must be True")
    if not m.no_network:
        errors.append("no_network must be True")
    return errors


def check_required_artifacts(output_dir: Path) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Check which required artifacts exist. Returns (present, missing)."""
    present, missing = [], []
    for name in REQUIRED_ARTIFACTS:
        (present if (output_dir / name).exists() else missing).append(name)
    return tuple(sorted(present)), tuple(sorted(missing))
