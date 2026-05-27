"""T915 — 500 backlog release hold.

Deterministic hold gate for T901-T960 backlog expansion.
No I/O. No timestamps. No random.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Prd500BacklogReleaseHold:
    hold_active: bool
    hold_scope: str
    hold_reasons: List[str]
    allowed_actions: List[str]
    forbidden_actions: List[str]
    release_conditions: List[str]
    final_verdict: str
    notes: List[str]


def build_prd_500_backlog_release_hold() -> Prd500BacklogReleaseHold:
    return Prd500BacklogReleaseHold(
        hold_active=True,
        hold_scope="T901-T960 backlog expansion",
        hold_reasons=[
            "FROZEN domain present",
            "no live trading authorization",
            "human review required",
            "500+ task backlog needs validation",
        ],
        allowed_actions=[
            "PRD planning",
            "pure tests",
            "static docs",
            "deterministic generation",
            "backlog materialization",
        ],
        forbidden_actions=[
            "live trading",
            "real order placement",
            "secret access",
            "exchange connection",
            "planner autonomous execution",
            "account state mutation",
        ],
        release_conditions=[
            "human approval granted",
            "all frozen tasks verified",
            "no live trading paths",
            "safety boundary check pass",
        ],
        final_verdict="HOLD",
        notes=[
            "release hold for 500+ backlog",
            "requires human approval before any execution",
        ],
    )


def release_hold_to_dict(hold: Prd500BacklogReleaseHold) -> Dict[str, object]:
    return {
        "hold_active": hold.hold_active,
        "hold_scope": hold.hold_scope,
        "hold_reasons": list(hold.hold_reasons),
        "allowed_actions": list(hold.allowed_actions),
        "forbidden_actions": list(hold.forbidden_actions),
        "release_conditions": list(hold.release_conditions),
        "final_verdict": hold.final_verdict,
        "notes": list(hold.notes),
    }


def release_hold_to_markdown(hold: Prd500BacklogReleaseHold) -> str:
    def _bullets(items: List[str]) -> str:
        return "\n".join(f"- {i}" for i in items)

    return (
        f"# 500 Backlog Release Hold\n\n"
        f"**Hold Active:** {hold.hold_active}\n\n"
        f"**Scope:** {hold.hold_scope}\n\n"
        f"## Hold Reasons\n{_bullets(hold.hold_reasons)}\n\n"
        f"## Allowed Actions\n{_bullets(hold.allowed_actions)}\n\n"
        f"## Forbidden Actions\n{_bullets(hold.forbidden_actions)}\n\n"
        f"## Release Conditions\n{_bullets(hold.release_conditions)}\n\n"
        f"**Final Verdict:** {hold.final_verdict}\n\n"
        f"## Notes\n{_bullets(hold.notes)}\n"
    )
