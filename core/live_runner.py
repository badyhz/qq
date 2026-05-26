from __future__ import annotations

from typing import Any, Optional

from core.failure_policy import ACTION_HALT, build_loop_result
from core.failure_policy import FailurePolicy
from core.preflight import READINESS_NOT_READY


class LiveRunner:
    """Thin wrapper that executes a single runtime loop step via ExecutionEngine."""

    def __init__(self, execution_engine: Any, failure_policy: Optional[FailurePolicy] = None):
        self.execution_engine = execution_engine
        self.failure_policy = failure_policy if isinstance(failure_policy, FailurePolicy) else FailurePolicy()

    def run_once(
        self,
        *,
        market_update: Optional[dict] = None,
        order_updates: Optional[list[dict]] = None,
        fill_updates: Optional[list[dict]] = None,
        connector: Optional[Any] = None,
    ) -> dict:
        if hasattr(self.execution_engine, "run_operational_readiness_check"):
            readiness = self.execution_engine.run_operational_readiness_check(connector=connector)
            if str(readiness.get("status", "")).upper() == READINESS_NOT_READY:
                reasons = [
                    f"preflight:{issue.get('code', 'unknown')}"
                    for issue in readiness.get("blocking_issues", [])
                ]
                if not reasons:
                    reasons = ["preflight:blocked"]
                return build_loop_result(ACTION_HALT, reasons, {"readiness": readiness})

        if hasattr(self.execution_engine, "run_preflight_checks"):
            preflight = self.execution_engine.run_preflight_checks(connector=connector)
            action = self.failure_policy.decide_from_preflight(preflight)
            if action == ACTION_HALT:
                reasons = [
                    f"preflight:{issue.get('code', 'unknown')}"
                    for issue in preflight.get("blocking_issues", [])
                ]
                if not reasons:
                    reasons = ["preflight:blocked"]
                return build_loop_result(action, reasons, {"preflight": preflight})
        return self.execution_engine.run_once(
            market_update=market_update,
            order_updates=order_updates,
            fill_updates=fill_updates,
            connector=connector,
        )

    def run_testnet_smoke(
        self,
        *,
        symbol: str = "BTCUSDT",
        connector: Optional[Any] = None,
        stale_order_seconds: int = 300,
    ) -> dict:
        if hasattr(self.execution_engine, "run_testnet_smoke"):
            return self.execution_engine.run_testnet_smoke(
                symbol=symbol,
                connector=connector,
                stale_order_seconds=stale_order_seconds,
            )
        return {
            "ok": False,
            "mode": "unknown",
            "environment": {"environment": "unknown"},
            "checked_steps": [],
            "warnings": [],
            "blocking_issues": [{"code": "testnet_smoke_not_supported", "message": "Execution engine has no smoke entrypoint."}],
            "summary": "testnet_smoke_not_supported",
        }

    def run_testnet_order_smoke(
        self,
        *,
        symbol: str = "BTCUSDT",
        side: str = "SHORT",
        price: float = 100.0,
        qty: float = 0.01,
        connector: Optional[Any] = None,
        stale_order_seconds: int = 300,
    ) -> dict:
        if hasattr(self.execution_engine, "run_testnet_order_smoke"):
            return self.execution_engine.run_testnet_order_smoke(
                symbol=symbol,
                side=side,
                price=price,
                qty=qty,
                connector=connector,
                stale_order_seconds=stale_order_seconds,
            )
        return {
            "ok": False,
            "submitted": False,
            "canceled": False,
            "mode": "unknown",
            "environment": {"environment": "unknown"},
            "order_id": "",
            "client_order_id": "",
            "observed_statuses": [],
            "warnings": [],
            "blocking_issues": [{"code": "testnet_order_smoke_not_supported", "message": "Execution engine has no order smoke entrypoint."}],
        }
