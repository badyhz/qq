"""Risk plan calculator for trade plans."""
from __future__ import annotations
from src.trade_plan_engine.models import RiskPlan, new_id, utc_now_iso

DEFAULT_EQUITY = 10000.0
DEFAULT_RISK_PER_TRADE = 0.005
DEFAULT_MAX_ACCOUNT_RISK = 0.01


def calculate_risk_plan(
    entry_price: float,
    stop_loss: float,
    account_equity: float = DEFAULT_EQUITY,
    risk_per_trade_pct: float = DEFAULT_RISK_PER_TRADE,
    max_account_risk_pct: float = DEFAULT_MAX_ACCOUNT_RISK,
) -> RiskPlan:
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit <= 0:
        risk_per_unit = entry_price * 0.03

    risk_amount = account_equity * risk_per_trade_pct
    suggested_qty = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
    suggested_notional = suggested_qty * entry_price
    risk_pct = (risk_per_unit / entry_price) * 100

    leverage_hint = 1
    if risk_pct > 0:
        leverage_hint = max(1, min(20, int(5.0 / risk_pct)))

    if risk_pct > 10:
        risk_level = "REJECTED"
        risk_notes = f"Risk {risk_pct:.1f}% exceeds 10% threshold — plan rejected"
    elif risk_pct > 6:
        risk_level = "HIGH"
        risk_notes = f"Risk {risk_pct:.1f}% exceeds 6% — plan downgraded"
    elif risk_pct > 3:
        risk_level = "MEDIUM"
        risk_notes = f"Risk {risk_pct:.1f}% — acceptable with caution"
    else:
        risk_level = "LOW"
        risk_notes = f"Risk {risk_pct:.1f}% — within normal range"

    return RiskPlan(
        risk_plan_id=new_id("RP"),
        account_equity_placeholder=account_equity,
        max_account_risk_pct=max_account_risk_pct,
        risk_per_trade_pct=risk_per_trade_pct,
        entry_price=entry_price,
        stop_loss=stop_loss,
        risk_per_unit=risk_per_unit,
        suggested_notional=round(suggested_notional, 2),
        suggested_quantity_placeholder=round(suggested_qty, 8),
        leverage_hint=leverage_hint,
        risk_level=risk_level,
        risk_notes=risk_notes,
    )
