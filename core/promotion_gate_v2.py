"""Promotion gate v2 — advisory-only promotion status.

Never promotes to runtime/testnet/live. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.research_quality_contract import RELEASE_HOLD_VALUE


@dataclass(frozen=True)
class PromotionDecision:
    """Advisory-only promotion decision."""
    status: str  # ADVISORY_PASS, ADVISORY_PARTIAL, ADVISORY_FAIL
    advisory_only: bool
    human_review_required: bool
    release_hold: str
    block_reasons: Tuple[str, ...]
    confidence: float


def evaluate_promotion_gate(
    composite_score: float,
    evidence_completeness: float,
    hard_blocks: List[str],
    min_score: float = 0.5,
    min_completeness: float = 0.8,
) -> PromotionDecision:
    """Evaluate promotion gate. Always advisory-only."""
    blocks = list(hard_blocks)

    if blocks:
        status = "ADVISORY_FAIL"
    elif composite_score < min_score:
        status = "ADVISORY_FAIL"
        blocks.append(f"LOW_COMPOSITE_SCORE:{composite_score:.4f}")
    elif evidence_completeness < min_completeness:
        status = "ADVISORY_PARTIAL"
        blocks.append(f"LOW_EVIDENCE_COMPLETENESS:{evidence_completeness:.4f}")
    else:
        status = "ADVISORY_PASS"

    confidence = min(composite_score, evidence_completeness)

    return PromotionDecision(
        status=status,
        advisory_only=True,
        human_review_required=True,
        release_hold=RELEASE_HOLD_VALUE,
        block_reasons=tuple(blocks),
        confidence=confidence,
    )


def build_promotion_gate_report(
    decision: PromotionDecision,
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build promotion_gate_v2.json."""
    return {
        "schema_version": "1.0.0",
        "generated_by": "promotion_gate_v2",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "status": decision.status,
        "advisory_only_status": decision.advisory_only,
        "human_review_required_flag": decision.human_review_required,
        "release_hold_value": decision.release_hold,
        "block_reasons": list(decision.block_reasons),
        "confidence": decision.confidence,
        "warnings": [],
        "hard_blocks": list(decision.block_reasons),
        "verdict": decision.status.replace("ADVISORY_", ""),
    }
