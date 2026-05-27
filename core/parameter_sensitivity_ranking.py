"""Parameter sensitivity ranking — rank parameters by sensitivity.

Pure functions. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


@dataclass(frozen=True)
class ParameterSensitivity:
    """Sensitivity ranking for a single parameter."""
    param_name: str
    sensitivity_score: float  # 0.0 = insensitive, 1.0 = highly sensitive
    rank: int
    reason: str


def compute_sensitivity_ranking(
    base_score: float,
    perturbation_results: Dict[str, List[float]],
) -> Tuple[ParameterSensitivity, ...]:
    """Compute sensitivity ranking from perturbation results.

    Higher sensitivity = score changes more when parameter is perturbed.
    """
    sensitivities = []
    for param_name, scores in sorted(perturbation_results.items()):
        valid_scores = [s for s in scores if s == s]
        if not valid_scores:
            sensitivities.append(ParameterSensitivity(param_name, 1.0, 0, "All NaN"))
            continue

        mean = sum(valid_scores) / len(valid_scores)
        diff = abs(mean - base_score)
        sensitivity = min(diff / max(abs(base_score), 0.001), 1.0)
        sensitivities.append(ParameterSensitivity(
            param_name, sensitivity, 0,
            f"Score delta={diff:.4f}, sensitivity={sensitivity:.4f}",
        ))

    # Rank by sensitivity (highest first)
    sensitivities = sorted(sensitivities, key=lambda x: -x.sensitivity_score)
    ranked = tuple(
        ParameterSensitivity(s.param_name, s.sensitivity_score, i + 1, s.reason)
        for i, s in enumerate(sensitivities)
    )
    return ranked


def build_sensitivity_ranking_report(
    rankings: Tuple[ParameterSensitivity, ...],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build parameter_sensitivity_ranking.json."""
    return {
        "schema_version": "1.0.0",
        "generated_by": "parameter_sensitivity_ranking",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "rankings": [
            {"param_name": r.param_name, "sensitivity_score": r.sensitivity_score,
             "rank": r.rank, "reason": r.reason}
            for r in rankings
        ],
        "total_parameters": len(rankings),
        "warnings": [],
        "hard_blocks": [],
        "verdict": "PASS",
    }
