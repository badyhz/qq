"""Trade intent risk gate — validates trade intents against safety rules.

No orders, no accounts, no secrets. Pure validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskGateResult:
    """Result of risk gate validation."""
    passed: bool
    status: str  # PASS / BLOCK / INVALID
    reasons: list[str]
    severity: str  # OK / WARN / BLOCK

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "status": self.status,
            "reasons": list(self.reasons),
            "severity": self.severity,
        }


FORBIDDEN_FIELDS = [
    "account_id", "api_key", "api_secret", "order_id",
    "exchange_order_id", "position_id", "broker_id",
]


def validate_trade_intent(intent: dict[str, Any]) -> RiskGateResult:
    """Validate a trade intent dict against risk gate rules."""
    reasons = []

    # Check forbidden fields
    for field in FORBIDDEN_FIELDS:
        if field in intent:
            reasons.append(f"forbidden field present: {field}")

    # Check execution_mode
    if intent.get("execution_mode") != "shadow_only":
        reasons.append(f"execution_mode must be shadow_only, got: {intent.get('execution_mode')}")

    # Check side
    side = intent.get("side")
    if side not in ("LONG", "SHORT", "NO_TRADE"):
        reasons.append(f"invalid side: {side}")

    # If already INVALID, short-circuit
    if intent.get("intent_status") == "INVALID":
        return RiskGateResult(
            passed=False, status="INVALID",
            reasons=reasons or ["intent_status is INVALID"],
            severity="BLOCK",
        )

    # Check rr_ratio
    rr = float(intent.get("rr_ratio") or 0)
    if rr < 1.5:
        reasons.append(f"rr_ratio {rr} < 1.5")

    # Check risk_distance_pct
    risk_dist = float(intent.get("risk_distance_pct") or 0)
    if risk_dist <= 0:
        reasons.append("risk_distance_pct <= 0")
    elif risk_dist > 5.0:
        reasons.append(f"risk_distance_pct {risk_dist}% > 5.0%")

    # Check reward vs risk
    reward_dist = float(intent.get("reward_distance_pct") or 0)
    if reward_dist > 0 and risk_dist > 0 and reward_dist <= risk_dist:
        reasons.append("reward_distance <= risk_distance")

    # Check max_risk_pct
    max_risk = float(intent.get("max_risk_pct") or 0)
    if max_risk > 0.5:
        reasons.append(f"max_risk_pct {max_risk}% > 0.5%")

    entry = float(intent.get("entry_price") or 0)
    sl = float(intent.get("stop_loss") or 0)
    tp = float(intent.get("take_profit") or 0)

    # Side-specific checks
    if side == "LONG":
        if sl > 0 and entry > 0 and sl >= entry:
            reasons.append("LONG stop_loss must be below entry_price")
        if tp > 0 and entry > 0 and tp <= entry:
            reasons.append("LONG take_profit must be above entry_price")
    elif side == "SHORT":
        if sl > 0 and entry > 0 and sl <= entry:
            reasons.append("SHORT stop_loss must be above entry_price")
        if tp > 0 and entry > 0 and tp >= entry:
            reasons.append("SHORT take_profit must be below entry_price")

    if reasons:
        return RiskGateResult(
            passed=False, status="BLOCK",
            reasons=reasons, severity="BLOCK",
        )

    return RiskGateResult(
        passed=True, status="PASS",
        reasons=[], severity="OK",
    )
