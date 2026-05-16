from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any


def validate_symbol_rules(rules: dict[str, Any] | None) -> dict[str, Any]:
    row = dict(rules or {})
    violations: list[str] = []
    tick_size = _to_float(row.get("tick_size", 0.0))
    step_size = _to_float(row.get("step_size", 0.0))
    min_qty = _to_float(row.get("min_qty", 0.0))
    min_notional = _to_float(row.get("min_notional", 0.0))
    price_precision = _to_int(row.get("price_precision", -1), default=-1)
    qty_precision = _to_int(row.get("qty_precision", -1), default=-1)
    if tick_size < 0:
        violations.append("invalid_tick_size")
    if step_size < 0:
        violations.append("invalid_step_size")
    if min_qty < 0:
        violations.append("invalid_min_qty")
    if min_notional < 0:
        violations.append("invalid_min_notional")
    if price_precision < -1:
        violations.append("invalid_price_precision")
    if qty_precision < -1:
        violations.append("invalid_qty_precision")
    return {
        "is_valid": len(violations) == 0,
        "violations": violations,
        "rules": {
            "tick_size": tick_size,
            "step_size": step_size,
            "min_qty": min_qty,
            "min_notional": min_notional,
            "price_precision": price_precision,
            "qty_precision": qty_precision,
        },
    }


def normalize_order_params(*, price: Any, qty: Any, rules: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_price = _to_float(price)
    normalized_qty = _to_float(qty)
    validation = validate_symbol_rules(rules)
    violations = list(validation["violations"])
    resolved_rules = validation["rules"]

    if normalized_price <= 0:
        violations.append("invalid_price")
    if normalized_qty <= 0:
        violations.append("invalid_qty")

    tick_size = resolved_rules["tick_size"]
    step_size = resolved_rules["step_size"]
    if normalized_price > 0 and tick_size > 0:
        normalized_price = _round_down(normalized_price, tick_size)
    elif normalized_price > 0 and resolved_rules["price_precision"] >= 0:
        normalized_price = _round_down_precision(normalized_price, resolved_rules["price_precision"])
    if normalized_qty > 0 and step_size > 0:
        normalized_qty = _round_down(normalized_qty, step_size)
    elif normalized_qty > 0 and resolved_rules["qty_precision"] >= 0:
        normalized_qty = _round_down_precision(normalized_qty, resolved_rules["qty_precision"])

    min_qty = resolved_rules["min_qty"]
    if min_qty > 0 and normalized_qty < min_qty:
        violations.append("min_qty_violation")

    notional = normalized_price * normalized_qty
    min_notional = resolved_rules["min_notional"]
    if min_notional > 0 and notional < min_notional:
        violations.append("min_notional_violation")

    return {
        "normalized_price": normalized_price,
        "normalized_qty": normalized_qty,
        "is_valid": len(violations) == 0,
        "violations": list(dict.fromkeys(violations)),
        "notional": notional,
        "rules": resolved_rules,
    }


def _round_down(value: float, step: float) -> float:
    step_decimal = Decimal(str(step))
    value_decimal = Decimal(str(value))
    rounded = (value_decimal / step_decimal).quantize(Decimal("1"), rounding=ROUND_DOWN) * step_decimal
    return float(rounded)


def _round_down_precision(value: float, precision: int) -> float:
    quantizer = Decimal("1").scaleb(-int(precision))
    return float(Decimal(str(value)).quantize(quantizer, rounding=ROUND_DOWN))


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value in ("", None):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
