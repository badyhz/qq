"""T18501 — Strategy Promotion Board.

Pure deterministic. No I/O. No network.
Evaluates strategies for promotion, rejection, freeze, or watchlist decisions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_BOARD_DECISIONS: tuple[str, ...] = (
    "PROMOTE",
    "HOLD",
    "REJECT",
    "FREEZE",
    "WATCHLIST",
)

FORBIDDEN_BOARD_DECISIONS: tuple[str, ...] = (
    "AUTO_PROMOTE",
    "FORCE_ACTIVATE",
    "LIVE_ENABLE",
    "SUBMIT_ENABLE",
)


@dataclass(frozen=True)
class PromotionBoardDecision:
    """Single strategy promotion board decision."""
    decision_id: str
    strategy_id: str
    strategy_name: str
    current_status: str
    board_decision: str
    decision_reason: str
    blockers: list[str]
    evidence_sufficient: bool
    tests_passed: bool
    next_action: str
    simulation_only: bool

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "current_status": self.current_status,
            "board_decision": self.board_decision,
            "decision_reason": self.decision_reason,
            "blockers": self.blockers,
            "evidence_sufficient": self.evidence_sufficient,
            "tests_passed": self.tests_passed,
            "next_action": self.next_action,
            "simulation_only": self.simulation_only,
        }


def _evaluate_strategy(strategy: dict) -> tuple[str, str, bool, bool]:
    """Evaluate a strategy for promotion board decision.

    Returns: (decision, reason, evidence_sufficient, tests_passed)
    """
    status = strategy.get("promotion_status", "RESEARCH_ONLY")
    blockers = strategy.get("blockers", [])
    test_status = strategy.get("test_status", "PENDING")

    has_blockers = len(blockers) > 0
    tests_passed = test_status == "PASSED"

    # Rejected strategies stay rejected
    if status == "REJECTED":
        return "REJECT", "already_rejected", False, tests_passed

    # Frozen strategies stay frozen
    if status == "FROZEN":
        return "FREEZE", "already_frozen", False, tests_passed

    # If there are blockers, hold
    if has_blockers:
        return "HOLD", f"blockers_present: {', '.join(blockers)}", False, tests_passed

    # Promotion path based on current status
    if status == "RESEARCH_ONLY":
        if tests_passed:
            return "WATCHLIST", "research_complete_can_move_to_watchlist", True, True
        return "HOLD", "needs_test_validation", False, False

    if status == "WATCHLIST_ONLY":
        return "WATCHLIST", "maintain_watchlist", True, tests_passed

    if status == "SHADOW_CANDIDATE":
        if tests_passed:
            return "PROMOTE", "ready_for_shadow_active", True, True
        return "HOLD", "needs_shadow_test_validation", False, False

    if status == "SHADOW_ACTIVE":
        return "HOLD", "maintain_shadow_active_collect_more_evidence", True, tests_passed

    if status == "TESTNET_DRY_RUN_CANDIDATE":
        return "HOLD", "awaiting_testnet_dry_run_approval", True, tests_passed

    return "HOLD", "unknown_status", False, False


def build_board_decision(strategy: dict) -> PromotionBoardDecision:
    """Build a single promotion board decision."""
    sid = strategy.get("strategy_id", "unknown")
    sname = strategy.get("strategy_name", "unknown")
    current = strategy.get("promotion_status", "RESEARCH_ONLY")
    blockers = strategy.get("blockers", [])

    decision, reason, evidence_ok, tests_ok = _evaluate_strategy(strategy)

    next_action_map = {
        "PROMOTE": "ADVANCE_TO_NEXT_STAGE",
        "HOLD": "COLLECT_MORE_EVIDENCE",
        "REJECT": "ARCHIVE_STRATEGY",
        "FREEZE": "MAINTAIN_FROZEN",
        "WATCHLIST": "MONITOR_WATCHLIST",
    }

    return PromotionBoardDecision(
        decision_id=f"board_{sid}",
        strategy_id=sid,
        strategy_name=sname,
        current_status=current,
        board_decision=decision,
        decision_reason=reason,
        blockers=blockers,
        evidence_sufficient=evidence_ok,
        tests_passed=tests_ok,
        next_action=next_action_map.get(decision, "REVIEW"),
        simulation_only=True,
    )


def build_promotion_board(
    strategies: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[PromotionBoardDecision]:
    """Build promotion board decisions for all strategies."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")
    return [build_board_decision(s) for s in strategies]


def compute_board_hash(decisions: list[PromotionBoardDecision]) -> str:
    raw = json.dumps([d.to_dict() for d in decisions], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_board_markdown(decisions: list[PromotionBoardDecision]) -> str:
    lines = [
        "# Strategy Promotion Board",
        "",
        f"**Total strategies:** {len(decisions)}",
        "",
        "## Decision Summary",
        "",
    ]

    decision_counts: dict[str, int] = {}
    for d in decisions:
        decision_counts[d.board_decision] = decision_counts.get(d.board_decision, 0) + 1
    for dec, count in sorted(decision_counts.items()):
        lines.append(f"- **{dec}:** {count}")

    lines.append("")
    lines.append("## Strategy Decisions")
    lines.append("")

    for d in decisions:
        lines.append(f"### {d.strategy_id}")
        lines.append("")
        lines.append(f"- **Name:** {d.strategy_name}")
        lines.append(f"- **Current status:** {d.current_status}")
        lines.append(f"- **Board decision:** {d.board_decision}")
        lines.append(f"- **Reason:** {d.decision_reason}")
        lines.append(f"- **Evidence sufficient:** {d.evidence_sufficient}")
        lines.append(f"- **Tests passed:** {d.tests_passed}")
        lines.append(f"- **Next action:** {d.next_action}")
        if d.blockers:
            lines.append(f"- **Blockers:** {', '.join(d.blockers)}")
        lines.append("")

    lines.append("---")
    lines.append("BOARD DECISIONS ONLY. NO REAL TRADING AUTHORIZED.")
    lines.append("")

    return "\n".join(lines)


def render_blockers_markdown(decisions: list[PromotionBoardDecision]) -> str:
    lines = [
        "# Strategy Blockers Report",
        "",
    ]

    blocked = [d for d in decisions if d.blockers]
    lines.append(f"**Strategies with blockers:** {len(blocked)}")
    lines.append("")

    for d in blocked:
        lines.append(f"### {d.strategy_id}")
        lines.append("")
        for b in d.blockers:
            lines.append(f"- {b}")
        lines.append("")

    if not blocked:
        lines.append("No blockers found.")
        lines.append("")

    return "\n".join(lines)


def render_next_actions_markdown(decisions: list[PromotionBoardDecision]) -> str:
    lines = [
        "# Strategy Next Actions",
        "",
    ]

    for d in decisions:
        lines.append(f"- **{d.strategy_id}:** {d.next_action}")

    lines.append("")
    return "\n".join(lines)


def write_json(decisions: list[PromotionBoardDecision], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps([d.to_dict() for d in decisions], indent=2),
        encoding="utf-8",
    )


def write_manifest(decisions: list[PromotionBoardDecision], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    decision_counts: dict[str, int] = {}
    for d in decisions:
        decision_counts[d.board_decision] = decision_counts.get(d.board_decision, 0) + 1
    manifest = {
        "total_strategies": len(decisions),
        "decision_counts": dict(sorted(decision_counts.items())),
        "release_hold": release_hold,
        "simulation_only": True,
        "board_hash": compute_board_hash(decisions),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(decisions: list[PromotionBoardDecision], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_board_markdown(decisions), encoding="utf-8")
