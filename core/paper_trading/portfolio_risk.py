"""Paper trading portfolio risk — local simulation only, no real accounts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus
from core.paper_trading.account_state import AccountState


@dataclass
class PortfolioRiskConfig:
    max_open_plans: int = 5
    max_daily_loss: float = 5000.0
    max_total_exposure: float = 50000.0
    consecutive_loss_cooldown: int = 3
    max_same_symbol_plans: int = 2
    block_duplicate_direction: bool = True


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str = ""


def check_portfolio_risk(
    plan: OrderPlan,
    account: AccountState,
    config: PortfolioRiskConfig,
) -> RiskCheckResult:
    """Check if a new plan is allowed under portfolio risk rules."""

    # Check account-level constraints
    allowed, reason = account.can_open_new_plan()
    if not allowed:
        return RiskCheckResult(False, reason)

    # Check max same symbol
    same_symbol = [p for p in account.open_plans if p.symbol == plan.symbol]
    if len(same_symbol) >= config.max_same_symbol_plans:
        return RiskCheckResult(
            False,
            f"Max {config.max_same_symbol_plans} plans for {plan.symbol} already open",
        )

    # Check duplicate direction
    if config.block_duplicate_direction:
        for p in same_symbol:
            if p.side == plan.side:
                return RiskCheckResult(
                    False,
                    f"Duplicate {plan.side.value} direction for {plan.symbol}",
                )

    # Check exposure limit
    new_exposure = account.total_exposure + plan.entry_price * plan.position_size
    if new_exposure > config.max_total_exposure:
        return RiskCheckResult(
            False,
            f"Exposure {new_exposure:.0f} would exceed limit {config.max_total_exposure:.0f}",
        )

    return RiskCheckResult(True)


def apply_portfolio_risk(
    plan: OrderPlan,
    account: AccountState,
    config: PortfolioRiskConfig,
) -> OrderPlan:
    """Apply portfolio risk check. Returns plan unchanged if approved, CANCELLED if rejected."""
    result = check_portfolio_risk(plan, account, config)
    if not result.approved:
        return plan.with_status(OrderStatus.CANCELLED)
    return plan
