"""T17501 — Shadow-to-Testnet Promotion Decision Engine.

Pure deterministic. No I/O. No network.
Evaluates promotion evidence and produces a promotion decision.
Decision can only be: CONTINUE_SHADOW_ONLY, READY_FOR_TESTNET_DRY_RUN_PREP, or BLOCKED.
Never outputs TESTNET_SUBMIT_ALLOWED or REAL_SUBMIT_ALLOWED.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_DECISIONS: tuple[str, ...] = (
    "CONTINUE_SHADOW_ONLY",
    "READY_FOR_TESTNET_DRY_RUN_PREP",
    "BLOCKED",
)

FORBIDDEN_DECISIONS: tuple[str, ...] = (
    "TESTNET_SUBMIT_ALLOWED",
    "REAL_SUBMIT_ALLOWED",
    "LIVE_TRADING_ALLOWED",
    "AUTO_SUBMIT_ENABLED",
)


@dataclass(frozen=True)
class PromotionDecision:
    """Promotion decision result."""
    decision_id: str
    decision: str
    reasons: list[str]
    denial_reasons: list[str]
    evidence_passed: list[str]
    evidence_failed: list[str]
    all_evidence_passed: bool
    any_critical_blocker: bool
    simulation_only: bool
    release_hold: str

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "decision": self.decision,
            "reasons": self.reasons,
            "denial_reasons": self.denial_reasons,
            "evidence_passed": self.evidence_passed,
            "evidence_failed": self.evidence_failed,
            "all_evidence_passed": self.all_evidence_passed,
            "any_critical_blocker": self.any_critical_blocker,
            "simulation_only": self.simulation_only,
            "release_hold": self.release_hold,
        }


@dataclass(frozen=True)
class DenialReason:
    """Single denial reason."""
    reason_id: str
    evidence_type: str
    description: str
    blocking: bool

    def to_dict(self) -> dict:
        return {
            "reason_id": self.reason_id,
            "evidence_type": self.evidence_type,
            "description": self.description,
            "blocking": self.blocking,
        }


def _evaluate_evidence(evidence_items: list[dict]) -> tuple[list[str], list[str], list[DenialReason]]:
    """Evaluate all evidence items.

    Returns: (passed, failed, denial_reasons)
    """
    passed: list[str] = []
    failed: list[str] = []
    denials: list[DenialReason] = []

    for item in evidence_items:
        etype = item.get("evidence_type", "unknown")
        status = item.get("status", "FAIL")
        desc = item.get("description", "")
        blocking = item.get("blocking", True)

        if status == "PASS":
            passed.append(etype)
        else:
            failed.append(etype)
            if blocking:
                denials.append(DenialReason(
                    reason_id=f"denial_{etype}",
                    evidence_type=etype,
                    description=desc,
                    blocking=True,
                ))

    return passed, failed, denials


def make_promotion_decision(
    evidence_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> PromotionDecision:
    """Make promotion decision based on evidence."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    passed, failed, denials = _evaluate_evidence(evidence_items)
    all_passed = len(failed) == 0
    any_blocker = any(d.blocking for d in denials)

    if all_passed:
        decision = "READY_FOR_TESTNET_DRY_RUN_PREP"
        reasons = ["all_evidence_passed"]
    elif any_blocker:
        decision = "BLOCKED"
        reasons = [f"blocking_failures: {', '.join(failed)}"]
    else:
        decision = "CONTINUE_SHADOW_ONLY"
        reasons = [f"non_blocking_failures: {', '.join(failed)}"]

    return PromotionDecision(
        decision_id="shadow_to_testnet_promotion",
        decision=decision,
        reasons=reasons,
        denial_reasons=[d.description for d in denials],
        evidence_passed=passed,
        evidence_failed=failed,
        all_evidence_passed=all_passed,
        any_critical_blocker=any_blocker,
        simulation_only=True,
        release_hold=release_hold,
    )


def compute_decision_hash(decision: PromotionDecision) -> str:
    raw = json.dumps(decision.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_decision_markdown(decision: PromotionDecision) -> str:
    lines = [
        "# Shadow-to-Testnet Promotion Decision",
        "",
        f"**Decision:** {decision.decision}",
        f"**release_hold:** {decision.release_hold}",
        f"**simulation_only:** {decision.simulation_only}",
        "",
        "## Safety Boundary",
        "",
        "- Decision is simulation-only.",
        "- No real testnet submit authorized.",
        "- No real submit authorized.",
        "- No live trading authorized.",
        "",
        "## Evidence Summary",
        "",
        f"- **Passed:** {len(decision.evidence_passed)}",
        f"- **Failed:** {len(decision.evidence_failed)}",
        f"- **All passed:** {decision.all_evidence_passed}",
        f"- **Any critical blocker:** {decision.any_critical_blocker}",
        "",
    ]

    if decision.evidence_passed:
        lines.append("### Passed Evidence")
        lines.append("")
        for e in decision.evidence_passed:
            lines.append(f"- {e}")
        lines.append("")

    if decision.evidence_failed:
        lines.append("### Failed Evidence")
        lines.append("")
        for e in decision.evidence_failed:
            lines.append(f"- {e}")
        lines.append("")

    if decision.denial_reasons:
        lines.append("## Denial Reasons")
        lines.append("")
        for r in decision.denial_reasons:
            lines.append(f"- {r}")
        lines.append("")

    lines.append("## Decision Reasons")
    lines.append("")
    for r in decision.reasons:
        lines.append(f"- {r}")
    lines.append("")
    lines.append("---")
    lines.append("SIMULATION ONLY. NO SUBMIT AUTHORIZED.")
    lines.append("")

    return "\n".join(lines)


def render_denial_reasons_markdown(denials: list[DenialReason]) -> str:
    lines = [
        "# Promotion Denial Reasons",
        "",
        f"**Total denials:** {len(denials)}",
        "",
    ]
    for d in denials:
        lines.append(f"- **{d.evidence_type}:** {d.description} (blocking={d.blocking})")
    lines.append("")
    return "\n".join(lines)


def write_json(decision: PromotionDecision, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(decision.to_dict(), indent=2), encoding="utf-8")


def write_manifest(decision: PromotionDecision, out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "decision": decision.decision,
        "all_evidence_passed": decision.all_evidence_passed,
        "any_critical_blocker": decision.any_critical_blocker,
        "release_hold": release_hold,
        "simulation_only": True,
        "decision_hash": compute_decision_hash(decision),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(decision: PromotionDecision, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_decision_markdown(decision), encoding="utf-8")
