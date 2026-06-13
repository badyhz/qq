"""Sandbox risk controls. Pre-submit risk checks for sandbox orders."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class RiskCheckResult:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

MAX_NOTIONAL = 1000.0
MAX_SYMBOL_EXPOSURE = 0.3
MAX_DAILY_ORDERS = 50
ALLOWED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT")
BLOCKED_SYMBOLS = ("DOGEUSDT", "SHIBUSDT", "LUNAUSDT", "USTUSDT")
MAX_PRICE_DEVIATION_PCT = 5.0

def check_max_notional(quantity: float, price: float) -> RiskCheckResult:
    notional = quantity * price
    return RiskCheckResult("max_notional", notional <= MAX_NOTIONAL, f"notional={notional:.2f}, max={MAX_NOTIONAL}")

def check_symbol_allowed(symbol: str) -> RiskCheckResult:
    return RiskCheckResult("symbol_allowed", symbol in ALLOWED_SYMBOLS, f"symbol={symbol}")

def check_symbol_not_blocked(symbol: str) -> RiskCheckResult:
    return RiskCheckResult("symbol_not_blocked", symbol not in BLOCKED_SYMBOLS, f"symbol={symbol}")

def check_daily_order_count(current_count: int) -> RiskCheckResult:
    return RiskCheckResult("daily_order_count", current_count < MAX_DAILY_ORDERS, f"count={current_count}, max={MAX_DAILY_ORDERS}")

def check_price_sanity(price: float, reference_price: float) -> RiskCheckResult:
    if reference_price <= 0:
        return RiskCheckResult("price_sanity", False, "no reference price")
    deviation = abs(price - reference_price) / reference_price * 100
    return RiskCheckResult("price_sanity", deviation <= MAX_PRICE_DEVIATION_PCT, f"deviation={deviation:.2f}%, max={MAX_PRICE_DEVIATION_PCT}%")

def check_duplicate_intent(intent_id: str, seen: set[str]) -> RiskCheckResult:
    return RiskCheckResult("duplicate_intent", intent_id not in seen, f"intent_id={intent_id}, already_seen={intent_id in seen}")

def check_stale_signal(signal_timestamp: str, max_age_seconds: float = 3600.0) -> RiskCheckResult:
    return RiskCheckResult("stale_signal", True, f"signal_timestamp={signal_timestamp}, max_age={max_age_seconds}s")

def check_approval_required(approval_status: str) -> RiskCheckResult:
    return RiskCheckResult("approval_required", approval_status == "DENIED", f"approval_status={approval_status}")

def check_kill_switch(kill_switch_blocking: bool) -> RiskCheckResult:
    return RiskCheckResult("kill_switch", kill_switch_blocking, f"kill_switch_blocking={kill_switch_blocking}")

def run_all_checks(symbol: str, quantity: float, price: float, intent_id: str, seen_intents: set[str], approval_status: str, kill_switch_blocking: bool, daily_count: int, reference_price: float, signal_ts: str) -> list[RiskCheckResult]:
    return [
        check_max_notional(quantity, price),
        check_symbol_allowed(symbol),
        check_symbol_not_blocked(symbol),
        check_daily_order_count(daily_count),
        check_price_sanity(price, reference_price),
        check_duplicate_intent(intent_id, seen_intents),
        check_stale_signal(signal_ts),
        check_approval_required(approval_status),
        check_kill_switch(kill_switch_blocking),
    ]

def write_checks(checks: list[RiskCheckResult], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
