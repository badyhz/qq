"""Regime failure report — per-regime scorecard and failure detection.

Advisory only. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from core.research_quality_contract import RELEASE_HOLD_VALUE


def detect_regime_failure(
    regime_scores: Dict[str, float],
    failure_threshold: float = -0.05,
) -> Dict[str, Any]:
    """Detect regimes where strategy fails."""
    failures = {}
    for regime, score in sorted(regime_scores.items()):
        if score < failure_threshold:
            failures[regime] = {"score": score, "threshold": failure_threshold}

    return {
        "failures": failures,
        "failure_count": len(failures),
        "has_failure": len(failures) > 0,
    }


def build_regime_failure_report(
    strategy_id: str,
    regime_scores: Dict[str, float],
    failure_threshold: float = -0.05,
    concentration_threshold: float = 0.8,
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build regime_failure_report.json."""
    failure_result = detect_regime_failure(regime_scores, failure_threshold)

    # Check concentration
    total = sum(abs(s) for s in regime_scores.values())
    concentrations = {k: abs(v) / max(total, 0.001) for k, v in regime_scores.items()}
    max_conc = max(concentrations.values()) if concentrations else 0

    warnings = []
    blocks = []

    if failure_result["has_failure"]:
        blocks.append("REGIME_FAILURE")
    if max_conc > concentration_threshold:
        dominant = max(concentrations, key=concentrations.get)
        warnings.append(f"REGIME_CONCENTRATION:{dominant}={max_conc:.4f}")

    return {
        "schema_version": "1.0.0",
        "generated_by": "regime_failure_report",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "strategy_id": strategy_id,
        "regime_scores": regime_scores,
        "concentrations": concentrations,
        "failures": failure_result["failures"],
        "failure_count": failure_result["failure_count"],
        "warnings": warnings,
        "hard_blocks": blocks,
        "verdict": "FAIL" if blocks else "PASS",
    }
