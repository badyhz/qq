"""Shadow gate evaluator — evaluates shadow results against gate criteria. No network."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from core.paper_trading.shadow_ledger import ShadowLedger


@dataclass(frozen=True)
class ShadowGateResult:
    """Result of shadow gate evaluation."""
    decision: str  # PASS / FAIL / EXTEND
    reasons: List[str]
    valid_plans: int
    high_count: int
    medium_count: int
    low_count: int
    high_medium_ratio: float
    low_ratio: float
    total_expectancy: float
    high_expectancy: float
    medium_expectancy: float
    low_expectancy: float
    profit_factor: float
    max_drawdown: float
    consecutive_losses: int
    data_quality_success_rate: float
    safety_violations: int


def evaluate_shadow_gate(ledger: ShadowLedger) -> ShadowGateResult:
    """Evaluate shadow results against Phase 10 gate criteria."""
    records = ledger.read_all()
    valid = [r for r in records if r.valid_plan]
    high = [r for r in valid if r.priority == "HIGH"]
    medium = [r for r in valid if r.priority == "MEDIUM"]
    low = [r for r in valid if r.priority == "LOW"]

    reasons: List[str] = []
    safety_violations = 0

    # Check safety violations
    for r in records:
        if "PAPER_ONLY" not in r.safety_flags:
            safety_violations += 1
        if "NO_REAL_ORDER" not in r.safety_flags:
            safety_violations += 1

    # Calculate metrics
    valid_count = len(valid)
    high_count = len(high)
    medium_count = len(medium)
    low_count = len(low)
    high_medium_ratio = (high_count + medium_count) / valid_count if valid_count > 0 else 0.0
    low_ratio = low_count / valid_count if valid_count > 0 else 0.0

    # Calculate expectancy by priority (only WIN/LOSS outcomes)
    def calc_expectancy(records_list):
        trading = [r for r in records_list if r.outcome in ("WIN", "LOSS")]
        if not trading:
            return None  # No trading outcomes — not applicable
        wins = [r for r in trading if r.outcome == "WIN"]
        losses = [r for r in trading if r.outcome == "LOSS"]
        win_rate = len(wins) / len(trading)
        avg_win = sum(r.pnl for r in wins) / len(wins) if wins else 0.0
        avg_loss = sum(r.pnl for r in losses) / len(losses) if losses else 0.0
        return (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    total_expectancy = calc_expectancy(valid)
    high_expectancy = calc_expectancy(high)
    medium_expectancy = calc_expectancy(medium)
    low_expectancy = calc_expectancy(low)

    # Calculate profit factor
    wins = [r for r in valid if r.outcome == "WIN"]
    losses = [r for r in valid if r.outcome == "LOSS"]
    total_win = sum(r.pnl for r in wins)
    total_loss = abs(sum(r.pnl for r in losses))
    profit_factor = total_win / total_loss if total_loss > 0 else float("inf")

    # Calculate max drawdown
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for r in sorted(valid, key=lambda x: x.timestamp):
        cumulative += r.pnl
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Calculate consecutive losses
    consecutive_losses = 0
    max_consecutive = 0
    for r in sorted(valid, key=lambda x: x.timestamp):
        if r.outcome == "LOSS":
            consecutive_losses += 1
            max_consecutive = max(max_consecutive, consecutive_losses)
        else:
            consecutive_losses = 0

    # Calculate data quality
    data_ok = sum(1 for r in records if r.data_quality_ok)
    data_quality_success_rate = data_ok / len(records) if records else 0.0

    # Apply gate criteria
    decision = "PASS"

    # Safety violations => FAIL
    if safety_violations > 0:
        decision = "FAIL"
        reasons.append(f"Safety violations: {safety_violations}")

    # Insufficient samples => EXTEND
    if valid_count < 30:
        if decision == "PASS":
            decision = "EXTEND"
        reasons.append(f"Insufficient valid plans: {valid_count} < 30")

    # Insufficient HIGH => EXTEND
    if high_count < 5:
        if decision == "PASS":
            decision = "EXTEND"
        reasons.append(f"Insufficient HIGH plans: {high_count} < 5")

    # Insufficient MEDIUM => EXTEND
    if medium_count < 10:
        if decision == "PASS":
            decision = "EXTEND"
        reasons.append(f"Insufficient MEDIUM plans: {medium_count} < 10")

    # LOW > 50% => FAIL or EXTEND
    if low_ratio > 0.5:
        if decision == "PASS":
            decision = "EXTEND"
        reasons.append(f"LOW plans dominate: {low_ratio:.1%} > 50%")

    # Negative expectancy => FAIL (only when trading outcomes exist)
    if total_expectancy is not None and total_expectancy <= 0:
        decision = "FAIL"
        reasons.append(f"Total expectancy <= 0: {total_expectancy:.4f}")

    # Low profit factor => FAIL (only when there are both wins and losses)
    if valid_count > 0 and losses and profit_factor <= 1.2:
        decision = "FAIL"
        reasons.append(f"Profit factor <= 1.2: {profit_factor:.4f}")

    # HIGH expectancy <= 0 => FAIL (only when HIGH plans have trading outcomes)
    if high_expectancy is not None and high_expectancy <= 0:
        decision = "FAIL"
        reasons.append(f"HIGH expectancy <= 0: {high_expectancy:.4f}")

    # No distinguishability => FAIL
    if high_count >= 5 and medium_count >= 5:
        if high_expectancy is not None and medium_expectancy is not None:
            if abs(high_expectancy - medium_expectancy) < 0.01 * abs(medium_expectancy):
                decision = "FAIL"
                reasons.append("HIGH/MEDIUM no distinguishability")

    if not reasons:
        reasons.append("All criteria met")

    return ShadowGateResult(
        decision=decision,
        reasons=reasons,
        valid_plans=valid_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        high_medium_ratio=round(high_medium_ratio, 4),
        low_ratio=round(low_ratio, 4),
        total_expectancy=round(total_expectancy or 0.0, 4),
        high_expectancy=round(high_expectancy or 0.0, 4),
        medium_expectancy=round(medium_expectancy or 0.0, 4),
        low_expectancy=round(low_expectancy or 0.0, 4),
        profit_factor=round(profit_factor, 4) if profit_factor != float("inf") else float("inf"),
        max_drawdown=round(max_drawdown, 2),
        consecutive_losses=max_consecutive,
        data_quality_success_rate=round(data_quality_success_rate, 4),
        safety_violations=safety_violations,
    )
