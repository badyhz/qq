from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class MarketDataRouter:
    """Lightweight multi-symbol snapshot/context router for execution."""

    def __init__(self):
        self._registry: dict[str, dict[str, Any]] = {}

    def register_symbol(self, symbol: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = _normalize_symbol(symbol)
        if not normalized:
            return {"accepted": False, "reason": "invalid_symbol", "symbol": normalized}
        row = self._registry.get(normalized)
        if row is None:
            row = {
                "symbol": normalized,
                "snapshot": None,
                "context": dict(context) if isinstance(context, dict) else {},
                "registered_at": _now_iso(),
                "updated_at": "",
            }
            self._registry[normalized] = row
            return {"accepted": True, "reason": "", "symbol": normalized, "created": True}
        if isinstance(context, dict):
            row_context = dict(row.get("context", {}))
            row_context.update(context)
            row["context"] = row_context
        return {"accepted": True, "reason": "", "symbol": normalized, "created": False}

    def update_market_snapshot(self, symbol: str, data: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_symbol(symbol)
        row = self._registry.get(normalized)
        if row is None:
            return {"accepted": False, "reason": "symbol_not_registered", "symbol": normalized}
        row["snapshot"] = dict(data) if isinstance(data, dict) else {}
        row["updated_at"] = _now_iso()
        return {"accepted": True, "reason": "", "symbol": normalized, "snapshot": dict(row["snapshot"])}

    def get_market_snapshot(self, symbol: str) -> dict[str, Any] | None:
        normalized = _normalize_symbol(symbol)
        row = self._registry.get(normalized)
        if row is None:
            return None
        snapshot = row.get("snapshot")
        return dict(snapshot) if isinstance(snapshot, dict) else None

    def get_symbol_context(self, symbol: str) -> dict[str, Any] | None:
        normalized = _normalize_symbol(symbol)
        row = self._registry.get(normalized)
        if row is None:
            return None
        context = row.get("context")
        return dict(context) if isinstance(context, dict) else {}

    def update_symbol_context(self, symbol: str, context: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_symbol(symbol)
        row = self._registry.get(normalized)
        if row is None:
            return {"accepted": False, "reason": "symbol_not_registered", "symbol": normalized}
        merged = dict(row.get("context", {}))
        if isinstance(context, dict):
            merged.update(context)
        row["context"] = merged
        return {"accepted": True, "reason": "", "symbol": normalized, "context": dict(merged)}

    def iter_active_symbols(self):
        for symbol in self.get_registered_symbols():
            yield symbol

    def get_registered_symbols(self) -> list[str]:
        return sorted(self._registry.keys())


def _normalize_symbol(symbol: Any) -> str:
    return str(symbol or "").strip().upper()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
