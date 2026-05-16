from datetime import datetime, timezone
from typing import Any, Optional


class CircuitBreaker:
    def __init__(
        self,
        *,
        max_consecutive_losses: int = 3,
        max_daily_net_loss: float = 1000.0,
        max_consecutive_rejections: int = 3,
    ):
        self.max_consecutive_losses = int(max_consecutive_losses)
        self.max_daily_net_loss = float(max_daily_net_loss)
        self.max_consecutive_rejections = int(max_consecutive_rejections)

        self.consecutive_losses = 0
        self.consecutive_rejections = 0
        self.daily_net_pnl = 0.0
        self.last_reset_date = _to_date(datetime.now(timezone.utc))
        self.consistency_blocked = False
        self.consistency_violations = []
        self.last_reason = ""

    def can_open_new_position(self, *, timestamp: Optional[Any] = None) -> dict:
        self.reset_if_needed(timestamp=timestamp)

        if self.consistency_blocked:
            return {"can_open": False, "reason": "circuit_breaker_consistency_failure"}
        if self.consecutive_losses >= self.max_consecutive_losses:
            return {"can_open": False, "reason": "circuit_breaker_consecutive_losses"}
        if self.consecutive_rejections >= self.max_consecutive_rejections:
            return {"can_open": False, "reason": "circuit_breaker_consecutive_rejections"}
        if self.daily_net_pnl <= -abs(self.max_daily_net_loss):
            return {"can_open": False, "reason": "circuit_breaker_daily_net_loss"}
        return {"can_open": True, "reason": ""}

    def record_trade_result(self, *, net_pnl: float, timestamp: Optional[Any] = None) -> None:
        self.reset_if_needed(timestamp=timestamp)
        pnl = float(net_pnl)
        self.daily_net_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
            self.last_reason = "loss"
        else:
            self.consecutive_losses = 0
            self.last_reason = "profit_or_flat"

    def record_rejection(self, reason: str = "") -> None:
        self.consecutive_rejections += 1
        self.last_reason = str(reason or "rejection")

    def record_open_success(self) -> None:
        self.consecutive_rejections = 0
        self.last_reason = "open_success"

    def record_consistency_failure(self, violations: list[str]) -> None:
        self.consistency_blocked = True
        self.consistency_violations = list(violations or [])
        self.last_reason = "consistency_failure"

    def reset_if_needed(self, *, timestamp: Optional[Any] = None, force: bool = False) -> None:
        current_date = _to_date(timestamp)
        if force:
            self.consecutive_losses = 0
            self.consecutive_rejections = 0
            self.daily_net_pnl = 0.0
            self.consistency_blocked = False
            self.consistency_violations = []
            self.last_reason = "manual_reset"
            self.last_reset_date = current_date
            return
        if current_date != self.last_reset_date:
            self.consecutive_losses = 0
            self.consecutive_rejections = 0
            self.daily_net_pnl = 0.0
            self.consistency_blocked = False
            self.consistency_violations = []
            self.last_reason = "daily_reset"
            self.last_reset_date = current_date

    def get_status(self) -> dict:
        return {
            "consecutive_losses": self.consecutive_losses,
            "consecutive_rejections": self.consecutive_rejections,
            "daily_net_pnl": self.daily_net_pnl,
            "consistency_blocked": self.consistency_blocked,
            "consistency_violations": list(self.consistency_violations),
            "last_reason": self.last_reason,
            "last_reset_date": self.last_reset_date.isoformat(),
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_daily_net_loss": self.max_daily_net_loss,
            "max_consecutive_rejections": self.max_consecutive_rejections,
        }


def _to_date(value: Optional[Any]) -> datetime.date:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date()
    if value in ("", None):
        return datetime.now(timezone.utc).date()
    text = str(value)
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc).date()
    except ValueError:
        return datetime.now(timezone.utc).date()
