from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def build_runtime_status(
    *,
    order_manager: Any,
    circuit_breaker_status: Optional[dict] = None,
    account_risk_snapshot: Optional[dict] = None,
    exposure_ratio_warn_threshold: float = 2.0,
    symbol_exposure_warn_ratio: float = 1.0,
    stale_order_seconds: int = 300,
    now: Optional[Any] = None,
) -> dict:
    alerts: list[dict] = []
    now_dt = _to_datetime(now) or datetime.now(timezone.utc)
    current_position = _current_position(order_manager)
    has_position = bool(current_position)
    active_snapshot = _active_orders_snapshot(order_manager)
    active_orders = list(active_snapshot.get("active_orders", []))
    active_protection_orders = list(active_snapshot.get("active_protection_orders", []))
    protection_orders = _protection_orders(order_manager, current_position)

    consistency_report = _consistency_report(order_manager)
    if not consistency_report.get("is_consistent", True):
        alerts.append(
            _alert(
                code="state_consistency_failed",
                severity="ERROR",
                message="State consistency check failed.",
                details={"violations": list(consistency_report.get("violations", []))},
            )
        )

    if circuit_breaker_status:
        breaker_reason = _circuit_breaker_reason(circuit_breaker_status)
        if breaker_reason:
            severity = "ERROR" if breaker_reason == "consistency_failure" else "WARN"
            alerts.append(
                _alert(
                    code="circuit_breaker_triggered",
                    severity=severity,
                    message=f"Circuit breaker triggered: {breaker_reason}.",
                )
            )

    if has_position and len(active_protection_orders) == 0:
        alerts.append(
            _alert(
                code="position_without_protection_orders",
                severity="WARN",
                message="Active position has no active protection orders.",
            )
        )

    if not has_position and len(active_protection_orders) > 0:
        alerts.append(
            _alert(
                code="orphan_active_protection_orders",
                severity="ERROR",
                message="Active protection orders exist while there is no active position.",
            )
        )

    if has_position:
        current_trade_id = str(current_position.get("trade_id", ""))
        mismatched = [
            row
            for row in active_protection_orders
            if current_trade_id and str(row.get("parent_trade_id", "")) != current_trade_id
        ]
        if mismatched:
            alerts.append(
                _alert(
                    code="protection_parent_trade_mismatch",
                    severity="ERROR",
                    message="Protection orders are not linked to the current position trade_id.",
                    details={"count": len(mismatched)},
                )
            )

    stale_ids = []
    for row in active_orders:
        status = str(row.get("status", "")).strip().upper()
        if status not in {"NEW", "ACCEPTED", "PARTIALLY_FILLED"}:
            continue
        order_ts = _to_datetime(row.get("timestamp"))
        if not order_ts:
            continue
        if (now_dt - order_ts).total_seconds() >= stale_order_seconds:
            stale_ids.append(str(row.get("order_id", "")))
    if stale_ids:
        alerts.append(
            _alert(
                code="stale_active_orders",
                severity="WARN",
                message="Some active orders have been pending for too long.",
                details={"order_ids": stale_ids, "threshold_seconds": stale_order_seconds},
            )
        )

    restore_warnings = list(getattr(order_manager, "last_restore_warnings", []) or [])
    if restore_warnings:
        alerts.append(
            _alert(
                code="restore_snapshot_incomplete",
                severity="WARN",
                message="Snapshot restore completed with missing fields.",
                details={"warnings": restore_warnings},
            )
        )

    if isinstance(account_risk_snapshot, dict):
        equity = float(account_risk_snapshot.get("equity", 0.0) or 0.0)
        exposure_ratio = float(account_risk_snapshot.get("exposure_ratio", 0.0) or 0.0)
        if exposure_ratio_warn_threshold > 0 and exposure_ratio >= exposure_ratio_warn_threshold:
            severity = "ERROR" if exposure_ratio >= exposure_ratio_warn_threshold * 1.5 else "WARN"
            alerts.append(
                _alert(
                    code="exposure_ratio_high",
                    severity=severity,
                    message="Total notional exposure ratio is above threshold.",
                    details={
                        "exposure_ratio": exposure_ratio,
                        "threshold": exposure_ratio_warn_threshold,
                    },
                )
            )
        symbol_exposures = account_risk_snapshot.get("symbol_exposures", {})
        if isinstance(symbol_exposures, dict) and equity > 0 and symbol_exposure_warn_ratio > 0:
            for symbol, row in symbol_exposures.items():
                if not isinstance(row, dict):
                    continue
                symbol_notional = float(row.get("notional", 0.0) or 0.0)
                symbol_ratio = symbol_notional / equity
                if symbol_ratio >= symbol_exposure_warn_ratio:
                    alerts.append(
                        _alert(
                            code="symbol_exposure_high",
                            severity="WARN",
                            message=f"Symbol exposure ratio is above threshold for {symbol}.",
                            details={
                                "symbol": str(symbol),
                                "symbol_exposure_ratio": symbol_ratio,
                                "threshold": symbol_exposure_warn_ratio,
                            },
                        )
                    )

    key_counts = {
        "active_orders": len(active_orders),
        "positions": 1 if has_position else 0,
        "protection_orders": len(protection_orders),
    }
    overall_status = "OK"
    if any(alert["severity"] == "ERROR" for alert in alerts):
        overall_status = "ERROR"
    elif alerts:
        overall_status = "WARN"
    return {
        "overall_status": overall_status,
        "alerts": alerts,
        "key_counts": key_counts,
    }


def format_runtime_alerts(status: dict) -> str:
    overall_status = str(status.get("overall_status", "OK"))
    key_counts = status.get("key_counts", {}) or {}
    lines = [
        f"overall_status={overall_status}",
        "key_counts: "
        f"active_orders={int(key_counts.get('active_orders', 0))}, "
        f"positions={int(key_counts.get('positions', 0))}, "
        f"protection_orders={int(key_counts.get('protection_orders', 0))}",
    ]
    alerts = status.get("alerts", []) or []
    if not alerts:
        lines.append("alerts: none")
        return "\n".join(lines)
    lines.append("alerts:")
    for alert in alerts:
        severity = str(alert.get("severity", "WARN"))
        code = str(alert.get("code", "unknown"))
        message = str(alert.get("message", ""))
        lines.append(f"- [{severity}] {code}: {message}")
    return "\n".join(lines)


def _active_orders_snapshot(order_manager: Any) -> dict:
    if hasattr(order_manager, "get_active_orders"):
        snapshot = order_manager.get_active_orders()
        if isinstance(snapshot, dict):
            return snapshot
    rows = []
    if hasattr(order_manager, "list_open_orders"):
        data = order_manager.list_open_orders()
        if isinstance(data, list):
            rows = [dict(row) for row in data if isinstance(row, dict)]
    return {
        "active_entry_orders": rows,
        "active_protection_orders": [],
        "active_orders": rows,
        "filled_orders": [],
        "canceled_orders": [],
        "rejected_orders": [],
    }


def _protection_orders(order_manager: Any, current_position: Optional[dict]) -> list[dict]:
    if not hasattr(order_manager, "get_protection_orders"):
        return []
    try:
        trade_id = current_position.get("trade_id") if isinstance(current_position, dict) else None
        rows = order_manager.get_protection_orders(trade_id)
    except Exception:
        return []
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def _current_position(order_manager: Any) -> Optional[dict]:
    if not hasattr(order_manager, "current_position"):
        return None
    position = order_manager.current_position()
    return dict(position) if isinstance(position, dict) else None


def _consistency_report(order_manager: Any) -> dict:
    if not hasattr(order_manager, "build_state_consistency_report"):
        return {"is_consistent": True, "violations": []}
    report = order_manager.build_state_consistency_report()
    if not isinstance(report, dict):
        return {"is_consistent": True, "violations": []}
    return {
        "is_consistent": bool(report.get("is_consistent", True)),
        "violations": list(report.get("violations", [])),
    }


def _circuit_breaker_reason(status: dict) -> str:
    if bool(status.get("consistency_blocked", False)):
        return "consistency_failure"
    if int(status.get("consecutive_losses", 0)) >= int(status.get("max_consecutive_losses", 0)):
        return "consecutive_losses"
    if int(status.get("consecutive_rejections", 0)) >= int(status.get("max_consecutive_rejections", 0)):
        return "consecutive_rejections"
    max_daily_loss = abs(float(status.get("max_daily_net_loss", 0.0)))
    daily_net = float(status.get("daily_net_pnl", 0.0))
    if max_daily_loss > 0 and daily_net <= -max_daily_loss:
        return "daily_net_loss"
    return ""


def _alert(*, code: str, severity: str, message: str, details: Optional[dict] = None) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "details": details or {},
    }


def _to_datetime(value: Optional[Any]) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value in ("", None):
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
