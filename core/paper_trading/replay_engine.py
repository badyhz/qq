"""Paper trading replay engine — local fixture replay, no network."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable

from core.paper_trading.order_plan import OrderPlan, OrderSide, OrderStatus, ExitReason
from core.paper_trading.risk_sizing import RiskSizingConfig, apply_risk_sizing
from core.paper_trading.exit_rules import ExitRuleConfig, evaluate_exits
from core.paper_trading.paper_ledger import PaperLedger, LedgerEntry
from core.paper_trading.human_approval_gate import HumanApprovalGate
from core.paper_trading.account_state import AccountState
from core.paper_trading.portfolio_risk import PortfolioRiskConfig, check_portfolio_risk


@dataclass
class ReplayBar:
    """Single K-line bar for replay."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class ReplayConfig:
    risk_config: RiskSizingConfig = field(default_factory=RiskSizingConfig)
    exit_config: ExitRuleConfig = field(default_factory=ExitRuleConfig)
    portfolio_config: PortfolioRiskConfig = field(default_factory=PortfolioRiskConfig)
    auto_approve: bool = True  # paper mode: auto-approve for simulation
    use_portfolio_risk: bool = False  # enable account/portfolio risk checks


@dataclass
class ReplayResult:
    bars_processed: int
    signals_generated: int
    plans_created: int
    plans_approved: int
    trades_executed: int
    ledger: PaperLedger
    plans_portfolio_rejected: int = 0
    account: Optional[AccountState] = None


def load_bars_from_fixture(fixture_path: str) -> List[ReplayBar]:
    """Load bars from a JSON fixture file."""
    import json
    with open(fixture_path, "r") as f:
        data = json.load(f)
    bars = []
    for item in data:
        bars.append(ReplayBar(
            timestamp=item.get("timestamp", ""),
            open=float(item["open"]),
            high=float(item["high"]),
            low=float(item["low"]),
            close=float(item["close"]),
            volume=float(item.get("volume", 0)),
        ))
    return bars


def run_replay(
    bars: List[ReplayBar],
    signal_fn: Callable[[List[ReplayBar], int], Optional[Dict[str, Any]]],
    config: ReplayConfig,
) -> ReplayResult:
    """Run replay simulation.

    Args:
        bars: K-line bars to replay
        signal_fn: Function that takes (bars, bar_index) and returns a signal envelope or None
        config: Replay configuration

    Returns:
        ReplayResult with ledger and statistics
    """
    ledger = PaperLedger()
    gate = HumanApprovalGate()
    account = AccountState(
        max_open_plans=config.portfolio_config.max_open_plans,
        max_daily_loss=config.portfolio_config.max_daily_loss,
        max_total_exposure=config.portfolio_config.max_total_exposure,
        consecutive_loss_cooldown=config.portfolio_config.consecutive_loss_cooldown,
    )
    active_plans: List[OrderPlan] = []
    signals_generated = 0
    plans_created = 0
    plans_approved = 0
    plans_portfolio_rejected = 0
    trades_executed = 0

    for i, bar in enumerate(bars):
        # Check exits for active plans
        closed_plans = []
        for plan in active_plans:
            # Track high-water mark
            if plan.side == OrderSide.BUY:
                hwm = max(b.high for b in bars[max(0, i-20):i+1])
            else:
                hwm = min(b.low for b in bars[max(0, i-20):i+1])

            exit_signal = evaluate_exits(
                plan, bar.close, hwm, i, config.exit_config,
            )

            if exit_signal:
                closed_plan = plan.with_status(
                    OrderStatus.SIMULATED_CLOSED,
                    exit_signal.reason,
                    exit_signal.pnl,
                )
                # RR actual
                risk = abs(plan.entry_price - plan.stop_loss) * plan.position_size
                rr_actual = exit_signal.pnl / risk if risk > 0 else 0

                ledger.record(LedgerEntry(
                    plan=closed_plan,
                    entry_bar=i,
                    exit_bar=i,
                    exit_price=exit_signal.exit_price,
                    exit_reason=exit_signal.reason,
                    pnl=exit_signal.pnl,
                    rr_actual=round(rr_actual, 2),
                ))
                trades_executed += 1
                closed_plans.append(plan)

                # Update account state
                if config.use_portfolio_risk:
                    account.close_plan(plan, exit_signal.pnl)

        active_plans = [p for p in active_plans if p not in closed_plans]

        # Generate signal
        envelope = signal_fn(bars, i)
        if envelope is None:
            continue

        signals_generated += 1

        # Convert to plan
        from core.paper_trading.signal_to_plan_adapter import signal_envelope_to_order_plan
        plan = signal_envelope_to_order_plan(envelope, "RPL", plans_created)
        if plan is None:
            continue

        plans_created += 1

        # Apply risk sizing (sets WAITING_FOR_HUMAN_APPROVAL if approved)
        plan = apply_risk_sizing(plan, config.risk_config)
        if plan.status == OrderStatus.CANCELLED:
            ledger.record(LedgerEntry(
                plan=plan, entry_bar=i, exit_bar=i,
                exit_price=0, exit_reason=ExitReason.SIGNAL_INVALIDATED,
                pnl=0, rr_actual=0,
            ))
            continue

        # Portfolio risk check
        if config.use_portfolio_risk:
            risk_result = check_portfolio_risk(plan, account, config.portfolio_config)
            if not risk_result.approved:
                plan = plan.with_status(OrderStatus.CANCELLED)
                plans_portfolio_rejected += 1
                ledger.record(LedgerEntry(
                    plan=plan, entry_bar=i, exit_bar=i,
                    exit_price=0, exit_reason=ExitReason.SIGNAL_INVALIDATED,
                    pnl=0, rr_actual=0,
                ))
                continue

        # plan is already WAITING_FOR_HUMAN_APPROVAL from apply_risk_sizing
        if config.auto_approve:
            plans_approved += 1
            active_plans.append(plan)
            if config.use_portfolio_risk:
                account.reserve_margin(plan)
        # In non-auto mode, plan stays WAITING_FOR_HUMAN_APPROVAL

    # Close remaining active plans at last bar
    if bars:
        last_bar = bars[-1]
        for plan in active_plans:
            closed_plan = plan.with_status(
                OrderStatus.SIMULATED_CLOSED,
                ExitReason.TIME_STOP,
                0,
            )
            ledger.record(LedgerEntry(
                plan=closed_plan,
                entry_bar=len(bars) - 1,
                exit_bar=len(bars) - 1,
                exit_price=last_bar.close,
                exit_reason=ExitReason.TIME_STOP,
                pnl=0,
                rr_actual=0,
            ))
            trades_executed += 1
            if config.use_portfolio_risk:
                account.close_plan(plan, 0)

    return ReplayResult(
        bars_processed=len(bars),
        signals_generated=signals_generated,
        plans_created=plans_created,
        plans_approved=plans_approved,
        plans_portfolio_rejected=plans_portfolio_rejected,
        trades_executed=trades_executed,
        ledger=ledger,
        account=account if config.use_portfolio_risk else None,
    )
