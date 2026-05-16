from typing import Any, Optional


REQUIRED_CLOSED_TRADE_FIELDS = (
    "trade_id",
    "symbol",
    "side",
    "entry_price",
    "exit_price",
    "quantity",
    "gross_pnl",
    "net_pnl",
    "total_fees",
    "fees_paid",
    "entry_time",
    "exit_time",
    "duration_sec",
    "exit_reason",
)


def build_state_consistency_report(
    *,
    has_position: bool,
    position: Optional[dict] = None,
    closed_trade: Optional[dict] = None,
) -> dict[str, Any]:
    violations = []

    if has_position and not position:
        violations.append("has_position_true_but_position_missing")
    if not has_position and position:
        violations.append("has_position_false_but_position_present")

    if position:
        _append_non_negative_check(
            violations, "margin_required_negative", _to_optional_float(position.get("margin_required"))
        )
        _append_non_negative_check(
            violations, "total_fees_negative", _to_optional_float(position.get("total_fees", position.get("fees_paid")))
        )
        quantity = _to_optional_float(position.get("quantity"))
        if quantity is None or quantity <= 0:
            violations.append("position_quantity_non_positive")

    if closed_trade:
        _validate_closed_trade(closed_trade, violations)

    snapshot = {
        "has_position": has_position,
        "position": dict(position) if isinstance(position, dict) else None,
        "closed_trade": dict(closed_trade) if isinstance(closed_trade, dict) else None,
    }
    return {
        "is_consistent": len(violations) == 0,
        "violations": violations,
        "snapshot": snapshot,
    }


def _validate_closed_trade(closed_trade: dict, violations: list[str]) -> None:
    missing = []
    for field in REQUIRED_CLOSED_TRADE_FIELDS:
        if closed_trade.get(field, None) in ("", None):
            missing.append(field)
    if missing:
        violations.append(f"missing_closed_trade_fields:{','.join(missing)}")

    _append_non_negative_check(
        violations, "closed_trade_margin_required_negative", _to_optional_float(closed_trade.get("margin_required"))
    )
    total_fees = _to_optional_float(closed_trade.get("total_fees", closed_trade.get("fees_paid")))
    _append_non_negative_check(violations, "closed_trade_total_fees_negative", total_fees)

    gross_pnl = _to_optional_float(closed_trade.get("gross_pnl"))
    net_pnl = _to_optional_float(closed_trade.get("net_pnl"))
    fees_paid = _to_optional_float(closed_trade.get("fees_paid"))
    if gross_pnl is not None and net_pnl is not None and total_fees is not None:
        expected_net = gross_pnl - total_fees
        if abs(net_pnl - expected_net) > 1e-6:
            violations.append("closed_trade_pnl_math_inconsistent")
    if fees_paid is not None and total_fees is not None and abs(fees_paid - total_fees) > 1e-6:
        violations.append("closed_trade_fee_fields_inconsistent")


def _append_non_negative_check(violations: list[str], violation_code: str, value: Optional[float]) -> None:
    if value is None:
        return
    if value < 0:
        violations.append(violation_code)


def _to_optional_float(value: Any) -> Optional[float]:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
