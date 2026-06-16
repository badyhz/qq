"""Paper trading account state — local simulation only, no real accounts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List

from core.paper_trading.order_plan import OrderPlan, OrderStatus


@dataclass
class AccountState:
    """Simulated account state for paper trading."""
    starting_balance: float = 100000.0
    available_balance: float = 100000.0
    reserved_margin: float = 0.0
    realized_pnl: float = 0.0
    open_plans: List[OrderPlan] = field(default_factory=list)
    max_open_plans: int = 5
    max_daily_loss: float = 5000.0
    max_total_exposure: float = 50000.0
    consecutive_loss_cooldown: int = 3
    daily_loss: float = 0.0
    consecutive_losses: int = 0
    _cooldown_active: bool = field(default=False, repr=False)

    @property
    def open_plan_count(self) -> int:
        return len(self.open_plans)

    @property
    def total_exposure(self) -> float:
        return sum(p.entry_price * p.position_size for p in self.open_plans)

    @property
    def equity(self) -> float:
        unrealized = sum(p.closed_pnl for p in self.open_plans)
        return self.available_balance + self.reserved_margin + unrealized

    @property
    def is_cooling_down(self) -> bool:
        return self._cooldown_active

    def can_open_new_plan(self) -> tuple[bool, str]:
        """Check if a new plan can be opened. Returns (allowed, reason)."""
        if self._cooldown_active:
            return False, f"Cooldown active after {self.consecutive_loss_cooldown} consecutive losses"

        if self.open_plan_count >= self.max_open_plans:
            return False, f"Max open plans ({self.max_open_plans}) reached"

        if self.daily_loss >= self.max_daily_loss:
            return False, f"Daily loss limit ({self.max_daily_loss}) reached"

        if self.total_exposure >= self.max_total_exposure:
            return False, f"Total exposure limit ({self.max_total_exposure}) reached"

        return True, ""

    def reserve_margin(self, plan: OrderPlan) -> None:
        """Reserve margin for an approved plan."""
        margin = plan.entry_price * plan.position_size
        self.reserved_margin += margin
        self.available_balance -= margin
        self.open_plans.append(plan)

    def close_plan(self, plan: OrderPlan, pnl: float) -> None:
        """Close a plan and update account state."""
        # Find and remove from open plans
        self.open_plans = [p for p in self.open_plans if p.plan_id != plan.plan_id]

        # Release margin
        margin = plan.entry_price * plan.position_size
        self.reserved_margin -= margin
        self.available_balance += margin

        # Update PnL
        self.realized_pnl += pnl
        self.available_balance += pnl

        # Track daily loss
        if pnl < 0:
            self.daily_loss += abs(pnl)
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.consecutive_loss_cooldown:
                self._cooldown_active = True
        else:
            self.consecutive_losses = 0
            self._cooldown_active = False

    def reset_daily(self) -> None:
        """Reset daily counters (call at start of new day)."""
        self.daily_loss = 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            "starting_balance": self.starting_balance,
            "available_balance": round(self.available_balance, 2),
            "reserved_margin": round(self.reserved_margin, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "equity": round(self.equity, 2),
            "open_plan_count": self.open_plan_count,
            "max_open_plans": self.max_open_plans,
            "daily_loss": round(self.daily_loss, 2),
            "max_daily_loss": self.max_daily_loss,
            "total_exposure": round(self.total_exposure, 2),
            "max_total_exposure": self.max_total_exposure,
            "consecutive_losses": self.consecutive_losses,
            "cooldown_active": self._cooldown_active,
        }
