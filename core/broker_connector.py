from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol


ACTIVE_ORDER_STATUSES = {"NEW", "ACCEPTED", "PARTIALLY_FILLED"}


class BrokerConnector(Protocol):
    def get_environment(self) -> dict[str, str]: ...

    def check_connector_connectivity(self) -> dict[str, Any]: ...

    def submit_order(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def cancel_order(self, order_id: str) -> dict[str, Any]: ...

    def get_order(self, order_id: str) -> dict[str, Any] | None: ...

    def get_open_orders(self) -> list[dict[str, Any]]: ...

    def get_positions(self) -> list[dict[str, Any]]: ...

    def get_account_snapshot(self) -> dict[str, Any]: ...

    def get_symbol_rules(self, symbol: str) -> dict[str, Any]: ...

    def get_exchange_info(self, symbols: list[str] | None = None) -> dict[str, Any]: ...

    def poll_order_updates(self) -> list[dict[str, Any]]: ...

    def poll_fills(self) -> list[dict[str, Any]]: ...


class FakeBrokerConnector:
    """In-memory broker connector used by unit tests and live-mode scaffolding."""

    def __init__(self, *, enabled: bool = True, symbol_rules: dict[str, dict[str, Any]] | None = None):
        self.enabled = enabled
        self.symbol_rules = dict(symbol_rules or {})
        self._sequence = 0
        self._orders: dict[str, dict[str, Any]] = {}
        self._positions: dict[str, dict[str, Any]] = {}
        self._order_updates: list[dict[str, Any]] = []
        self._fills: list[dict[str, Any]] = []

    def is_enabled(self) -> bool:
        return bool(self.enabled)

    def get_environment(self) -> dict[str, str]:
        return {"mode": "live", "environment": "test-double"}

    def check_connector_connectivity(self) -> dict[str, Any]:
        return {
            "success": bool(self.enabled),
            "mode": "live",
            "environment": "test-double",
            "checked_items": {"fake_connector": True, "enabled": bool(self.enabled)},
            "warnings": [],
            "error": "" if self.enabled else "fake_connector_disabled",
        }

    def submit_order(self, request: dict[str, Any]) -> dict[str, Any]:
        symbol = str(request.get("symbol", "")).strip().upper()
        side = str(request.get("side", "")).strip().upper()
        qty = _to_float(request.get("qty", request.get("quantity", 0.0)))
        status = str(request.get("status", request.get("force_status", "FILLED"))).strip().upper() or "FILLED"
        order_id = str(request.get("order_id") or self._next_order_id())
        request_id = _pick_str(request, ("request_id", "client_order_id", "idempotency_key"))
        avg_fill_price = _to_float(request.get("avg_fill_price", request.get("entry_price", 0.0)))

        if not self.enabled:
            status = "REJECTED"
        if qty <= 0:
            status = "REJECTED"

        if status in {"REJECTED", "CANCELED"}:
            filled_qty = 0.0
            remaining_qty = max(qty, 0.0)
        elif status in {"NEW", "ACCEPTED"}:
            filled_qty = 0.0
            remaining_qty = max(qty, 0.0)
        elif status == "PARTIALLY_FILLED":
            filled_qty = _to_float(request.get("filled_qty", qty * 0.5))
            filled_qty = min(max(filled_qty, 0.0), max(qty, 0.0))
            remaining_qty = max(qty - filled_qty, 0.0)
        else:
            status = "FILLED"
            filled_qty = max(qty, 0.0)
            remaining_qty = 0.0

        normalized = {
            "accepted": status not in {"REJECTED", "CANCELED"},
            "order_id": order_id,
            "client_order_id": request_id,
            "request_id": request_id,
            "trade_id": request.get("trade_id"),
            "symbol": symbol,
            "side": side,
            "status": status,
            "qty": max(qty, 0.0),
            "filled_qty": filled_qty,
            "remaining_qty": remaining_qty,
            "avg_fill_price": avg_fill_price,
            "timestamp": _normalize_timestamp(request.get("timestamp")),
            "reason": "" if status not in {"REJECTED", "CANCELED"} else str(request.get("reason", "rejected")),
        }
        self._orders[order_id] = dict(normalized)
        if status in ACTIVE_ORDER_STATUSES:
            self._order_updates.append(
                {
                    "order_id": order_id,
                    "trade_id": normalized.get("trade_id"),
                    "symbol": symbol,
                    "side": side,
                    "status": "NEW",
                    "qty": normalized["qty"],
                    "filled_qty": 0.0,
                    "remaining_qty": normalized["qty"],
                    "avg_fill_price": 0.0,
                    "timestamp": normalized["timestamp"],
                }
            )
        self._order_updates.append(dict(normalized))

        if filled_qty > 0:
            self._fills.append(
                {
                    "fill_id": f"{order_id}:{filled_qty}:{avg_fill_price}:{normalized['timestamp']}",
                    "order_id": order_id,
                    "trade_id": normalized.get("trade_id"),
                    "symbol": symbol,
                    "side": side,
                    "qty": normalized["qty"],
                    "filled_qty": filled_qty,
                    "remaining_qty": remaining_qty,
                    "avg_fill_price": avg_fill_price,
                    "status": status,
                    "timestamp": normalized["timestamp"],
                }
            )
            self._update_positions(normalized)
        return dict(normalized)

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        key = str(order_id)
        order = self._orders.get(key)
        if not isinstance(order, dict):
            return {"accepted": False, "reason": "order_not_found"}
        order["status"] = "CANCELED"
        order["accepted"] = True
        order["remaining_qty"] = max(_to_float(order.get("qty", 0.0)) - _to_float(order.get("filled_qty", 0.0)), 0.0)
        order["timestamp"] = _normalize_timestamp(None)
        self._order_updates.append(dict(order))
        return dict(order)

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        order = self._orders.get(str(order_id))
        return dict(order) if isinstance(order, dict) else None

    def get_open_orders(self) -> list[dict[str, Any]]:
        rows = [
            dict(order)
            for order in self._orders.values()
            if str(order.get("status", "")).strip().upper() in ACTIVE_ORDER_STATUSES
        ]
        rows.sort(key=lambda row: str(row.get("order_id", "")))
        return rows

    def get_positions(self) -> list[dict[str, Any]]:
        rows = [dict(position) for position in self._positions.values()]
        rows.sort(key=lambda row: str(row.get("symbol", "")))
        return rows

    def get_account_snapshot(self) -> dict[str, Any]:
        return {
            "equity": 0.0,
            "available_balance": 0.0,
            "used_margin": 0.0,
            "positions": self.get_positions(),
        }

    def get_symbol_rules(self, symbol: str) -> dict[str, Any]:
        return dict(self.symbol_rules.get(str(symbol or "").strip().upper(), {}))

    def get_exchange_info(self, symbols: list[str] | None = None) -> dict[str, Any]:
        requested = {
            str(symbol or "").strip().upper()
            for symbol in list(symbols or [])
            if str(symbol or "").strip()
        }
        rows: list[dict[str, Any]] = []
        for symbol, rules in self.symbol_rules.items():
            normalized_symbol = str(symbol or "").strip().upper()
            if requested and normalized_symbol not in requested:
                continue
            rows.append(
                {
                    "symbol": normalized_symbol,
                    "pricePrecision": int(_to_float(rules.get("price_precision", 8), default=8)),
                    "quantityPrecision": int(_to_float(rules.get("qty_precision", 8), default=8)),
                    "filters": [
                        {"filterType": "PRICE_FILTER", "tickSize": str(rules.get("tick_size", 0.0))},
                        {
                            "filterType": "LOT_SIZE",
                            "stepSize": str(rules.get("step_size", 0.0)),
                            "minQty": str(rules.get("min_qty", 0.0)),
                        },
                        {"filterType": "MIN_NOTIONAL", "minNotional": str(rules.get("min_notional", 0.0))},
                    ],
                }
            )
        return {"symbols": rows}

    def poll_order_updates(self) -> list[dict[str, Any]]:
        rows = [dict(row) for row in self._order_updates]
        self._order_updates = []
        return rows

    def poll_fills(self) -> list[dict[str, Any]]:
        rows = [dict(row) for row in self._fills]
        self._fills = []
        return rows

    def _next_order_id(self) -> str:
        self._sequence += 1
        return f"FB-{self._sequence}"

    def _update_positions(self, order: dict[str, Any]) -> None:
        if str(order.get("status", "")).strip().upper() not in {"PARTIALLY_FILLED", "FILLED"}:
            return
        symbol = str(order.get("symbol", "")).strip().upper()
        if not symbol:
            return
        qty = _to_float(order.get("filled_qty", 0.0))
        if qty <= 0:
            return
        side = str(order.get("side", "")).strip().upper()
        signed_qty = -qty if side == "SHORT" else qty
        existing = self._positions.get(symbol)
        if existing is None:
            self._positions[symbol] = {
                "symbol": symbol,
                "qty": signed_qty,
                "entry_price": _to_float(order.get("avg_fill_price", 0.0)),
            }
            return
        combined_qty = _to_float(existing.get("qty", 0.0)) + signed_qty
        existing["qty"] = combined_qty
        if abs(combined_qty) <= 1e-12:
            self._positions.pop(symbol, None)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pick_str(row: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value in ("", None):
            continue
        return str(value)
    return default


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value not in ("", None):
        return str(value)
    return datetime.now(timezone.utc).isoformat()
