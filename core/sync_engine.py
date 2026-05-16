from __future__ import annotations

from typing import Any, Callable


class SyncEngine:
    """Deduplicates and forwards broker order/fill updates to execution consumers."""

    def __init__(self):
        self._seen_order_update_keys: set[tuple[Any, ...]] = set()
        self._seen_fill_keys: set[tuple[Any, ...]] = set()

    def process_order_updates(
        self,
        updates: list[dict[str, Any]],
        *,
        consumer: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        summary = {
            "total": len(updates),
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "results": [],
        }
        for update in updates:
            if not isinstance(update, dict):
                summary["errors"] += 1
                summary["results"].append({"ok": False, "reason": "invalid_update_payload", "update": update})
                continue
            key = self._build_order_update_key(update)
            if key in self._seen_order_update_keys:
                summary["skipped"] += 1
                summary["results"].append({"ok": True, "skipped": True, "reason": "duplicate_order_update", "update": dict(update)})
                continue
            self._seen_order_update_keys.add(key)
            consumed = consumer(update)
            if consumed.get("ok"):
                summary["processed"] += 1
            else:
                summary["errors"] += 1
            summary["results"].append(consumed)
        return summary

    def process_fill_updates(
        self,
        fills: list[dict[str, Any]],
        *,
        fill_to_update: Callable[[dict[str, Any]], dict[str, Any]],
        consumer: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        summary = {
            "total": len(fills),
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "results": [],
        }
        for fill in fills:
            if not isinstance(fill, dict):
                summary["errors"] += 1
                summary["results"].append({"ok": False, "reason": "invalid_fill_payload", "fill": fill})
                continue
            fill_key = self._build_fill_key(fill)
            if fill_key in self._seen_fill_keys:
                summary["skipped"] += 1
                summary["results"].append({"ok": True, "skipped": True, "reason": "duplicate_fill", "fill": dict(fill)})
                continue
            self._seen_fill_keys.add(fill_key)
            mapped = fill_to_update(fill)
            if not isinstance(mapped, dict):
                summary["errors"] += 1
                summary["results"].append({"ok": False, "reason": "invalid_mapped_order_update", "fill": dict(fill)})
                continue
            order_key = self._build_order_update_key(mapped)
            if order_key in self._seen_order_update_keys:
                summary["skipped"] += 1
                summary["results"].append({"ok": True, "skipped": True, "reason": "duplicate_order_update", "update": mapped})
                continue
            self._seen_order_update_keys.add(order_key)
            consumed = consumer(mapped)
            if consumed.get("ok"):
                summary["processed"] += 1
            else:
                summary["errors"] += 1
            summary["results"].append(consumed)
        return summary

    def _build_order_update_key(self, update: dict[str, Any]) -> tuple[Any, ...]:
        return (
            str(update.get("order_id", "")).strip(),
            str(update.get("trade_id", "")).strip(),
            str(update.get("status", "")).strip().upper(),
            _to_float(update.get("filled_qty", 0.0)),
            _to_float(update.get("remaining_qty", 0.0)),
            _to_float(update.get("avg_fill_price", update.get("avg_price", 0.0))),
            str(update.get("timestamp", "")).strip(),
        )

    def _build_fill_key(self, fill: dict[str, Any]) -> tuple[Any, ...]:
        explicit_fill_id = fill.get("fill_id")
        if explicit_fill_id not in ("", None):
            return ("fill_id", str(explicit_fill_id))
        return (
            str(fill.get("order_id", "")).strip(),
            str(fill.get("trade_id", "")).strip(),
            _to_float(fill.get("filled_qty", fill.get("qty", 0.0))),
            _to_float(fill.get("avg_fill_price", fill.get("price", 0.0))),
            str(fill.get("timestamp", "")).strip(),
        )


def _to_float(value: Any, default: float = 0.0) -> float:
    if value in ("", None):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
