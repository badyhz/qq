"""Research quality score — composite quality score and evidence completeness.

No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


def compute_composite_score(
    component_scores: Dict[str, float],
    weights: Dict[str, float] = None,
) -> float:
    """Compute weighted composite quality score."""
    if not component_scores:
        return 0.0

    if weights is None:
        weights = {k: 1.0 for k in component_scores}

    total_weight = 0
    weighted_sum = 0
    for k, v in component_scores.items():
        w = weights.get(k, 1.0)
        weighted_sum += v * w
        total_weight += w

    return weighted_sum / max(total_weight, 0.001)


def compute_evidence_completeness(
    required_evidence: List[str],
    present_evidence: List[str],
) -> float:
    """Compute evidence completeness score (0.0 to 1.0)."""
    if not required_evidence:
        return 1.0
    present = set(present_evidence) & set(required_evidence)
    return len(present) / len(required_evidence)


def build_quality_gate_summary(
    component_scores: Dict[str, float],
    evidence: List[str],
    required_evidence: List[str],
    hard_blocks: List[str],
    warnings: List[str],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build quality_gate_summary.json."""
    composite = compute_composite_score(component_scores)
    completeness = compute_evidence_completeness(required_evidence, evidence)

    if hard_blocks:
        verdict = "FAIL"
    elif completeness < 0.8:
        verdict = "PARTIAL"
    else:
        verdict = "PASS"

    # Confidence bands
    ci_lower = max(0, composite - 0.1)
    ci_upper = min(1.0, composite + 0.1)

    return {
        "schema_version": "1.0.0",
        "generated_by": "research_quality_score",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "composite_score": composite,
        "evidence_completeness": completeness,
        "confidence_band": {"lower": ci_lower, "upper": ci_upper},
        "component_scores": component_scores,
        "hard_blocks": hard_blocks,
        "warnings": warnings,
        "verdict": verdict,
    }
