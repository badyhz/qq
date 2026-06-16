"""Risk explainer — human-readable rejection reasons, no network."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReasonCode(str, Enum):
    RR_TOO_LOW = "RR_TOO_LOW"
    MAX_OPEN_PLANS = "MAX_OPEN_PLANS"
    MAX_TOTAL_EXPOSURE = "MAX_TOTAL_EXPOSURE"
    DUPLICATE_SYMBOL_DIRECTION = "DUPLICATE_SYMBOL_DIRECTION"
    MAX_DAILY_LOSS = "MAX_DAILY_LOSS"
    CONSECUTIVE_LOSS_COOLDOWN = "CONSECUTIVE_LOSS_COOLDOWN"
    MALFORMED_FIXTURE = "MALFORMED_FIXTURE"
    NO_SIGNAL = "NO_SIGNAL"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class RiskExplanation:
    reason_code: ReasonCode
    severity: Severity
    human_message: str
    suggested_action: str
    safe_to_retry: bool


_EXPLANATIONS = {
    ReasonCode.RR_TOO_LOW: RiskExplanation(
        reason_code=ReasonCode.RR_TOO_LOW,
        severity=Severity.WARNING,
        human_message="Risk/reward ratio too low. The potential loss is large relative to the potential gain.",
        suggested_action="Increase take_profit or decrease stop_loss to improve RR ratio above minimum threshold.",
        safe_to_retry=True,
    ),
    ReasonCode.MAX_OPEN_PLANS: RiskExplanation(
        reason_code=ReasonCode.MAX_OPEN_PLANS,
        severity=Severity.WARNING,
        human_message="Maximum number of open plans reached. Cannot open more positions.",
        suggested_action="Wait for existing plans to close, or increase max_open_plans in portfolio config.",
        safe_to_retry=True,
    ),
    ReasonCode.MAX_TOTAL_EXPOSURE: RiskExplanation(
        reason_code=ReasonCode.MAX_TOTAL_EXPOSURE,
        severity=Severity.CRITICAL,
        human_message="Total margin exposure at maximum. No additional positions can be opened.",
        suggested_action="Close existing positions or increase max_total_exposure limit.",
        safe_to_retry=True,
    ),
    ReasonCode.DUPLICATE_SYMBOL_DIRECTION: RiskExplanation(
        reason_code=ReasonCode.DUPLICATE_SYMBOL_DIRECTION,
        severity=Severity.WARNING,
        human_message="Already have an open plan in the same direction for this symbol.",
        suggested_action="Wait for the existing plan to close, or use a different symbol.",
        safe_to_retry=True,
    ),
    ReasonCode.MAX_DAILY_LOSS: RiskExplanation(
        reason_code=ReasonCode.MAX_DAILY_LOSS,
        severity=Severity.CRITICAL,
        human_message="Daily loss limit reached. Trading paused for today.",
        suggested_action="Wait until next trading day, or review strategy for excessive losses.",
        safe_to_retry=False,
    ),
    ReasonCode.CONSECUTIVE_LOSS_COOLDOWN: RiskExplanation(
        reason_code=ReasonCode.CONSECUTIVE_LOSS_COOLDOWN,
        severity=Severity.CRITICAL,
        human_message="Too many consecutive losses. Cooldown period active.",
        suggested_action="Wait for cooldown to expire, then review strategy quality before resuming.",
        safe_to_retry=False,
    ),
    ReasonCode.MALFORMED_FIXTURE: RiskExplanation(
        reason_code=ReasonCode.MALFORMED_FIXTURE,
        severity=Severity.WARNING,
        human_message="Fixture file contains invalid data (missing fields, wrong types).",
        suggested_action="Fix the fixture JSON file. Ensure all bars have valid open/high/low/close values.",
        safe_to_retry=False,
    ),
    ReasonCode.NO_SIGNAL: RiskExplanation(
        reason_code=ReasonCode.NO_SIGNAL,
        severity=Severity.INFO,
        human_message="No trading signal generated for this bar. Market conditions did not meet criteria.",
        suggested_action="No action needed. This is normal — signals only fire on qualifying patterns.",
        safe_to_retry=True,
    ),
    ReasonCode.UNKNOWN: RiskExplanation(
        reason_code=ReasonCode.UNKNOWN,
        severity=Severity.WARNING,
        human_message="An unspecified rejection occurred.",
        suggested_action="Check logs for details. Review signal and risk configuration.",
        safe_to_retry=True,
    ),
}


def explain(code: ReasonCode) -> RiskExplanation:
    """Get human-readable explanation for a rejection reason code."""
    return _EXPLANATIONS.get(code, _EXPLANATIONS[ReasonCode.UNKNOWN])


def explain_rr_too_low(actual_rr: float, min_rr: float) -> RiskExplanation:
    """Explain RR rejection with specific values."""
    base = explain(ReasonCode.RR_TOO_LOW)
    return RiskExplanation(
        reason_code=base.reason_code,
        severity=base.severity,
        human_message=f"Risk/reward ratio {actual_rr:.2f} is below minimum {min_rr:.2f}.",
        suggested_action=f"Increase take_profit or decrease stop_loss to achieve RR >= {min_rr:.2f}.",
        safe_to_retry=base.safe_to_retry,
    )
