from __future__ import annotations

from typing import Any, Optional

from core.binance_exchange_info import parse_binance_exchange_info


def resolve_symbol_rules(
    *,
    symbol: str,
    config_rules: Optional[dict[str, Any]] = None,
    connector: Any = None,
) -> dict[str, Any]:
    resolved_symbol = str(symbol or "").strip().upper()
    rules = dict((config_rules or {}).get(resolved_symbol, {}))
    if connector is not None and hasattr(connector, "get_symbol_rules"):
        connector_rules = connector.get_symbol_rules(resolved_symbol)
        if isinstance(connector_rules, dict):
            merged = dict(rules)
            merged.update({k: v for k, v in connector_rules.items() if v not in (None, "")})
            return merged
    return rules


def parse_exchange_info(
    payload: Any,
    *,
    symbols: Optional[list[str]] = None,
) -> dict[str, Any]:
    return parse_binance_exchange_info(payload, symbols=symbols)


def sync_symbol_rules(
    *,
    existing_rules: Optional[dict[str, dict[str, Any]]] = None,
    exchange_info: Any,
    symbols: Optional[list[str]] = None,
) -> dict[str, Any]:
    parsed = parse_exchange_info(exchange_info, symbols=symbols)
    merged_rules = {
        str(symbol or "").strip().upper(): dict(rule)
        for symbol, rule in dict(existing_rules or {}).items()
        if str(symbol or "").strip()
    }
    incoming_rules = dict(parsed.get("rules", {}))
    for symbol, rule in incoming_rules.items():
        normalized_symbol = str(symbol or "").strip().upper()
        if normalized_symbol == "":
            continue
        merged_rules[normalized_symbol] = dict(rule or {})
    return {
        "success": bool(parsed.get("success", False)),
        "rules": merged_rules,
        "synced_rules": incoming_rules,
        "warnings": list(parsed.get("warnings", [])),
        "missing_symbols": list(parsed.get("missing_symbols", [])),
        "found_symbols": list(parsed.get("found_symbols", [])),
    }
