"""Operator state writer. Aggregates runtime artifacts into system state."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RuntimeSystemState:
    state_id: str
    current_mode: str
    submit_permission: str
    real_submit_allowed: bool
    testnet_submit_allowed: bool
    dry_run_allowed: bool
    system_healthy: bool
    dry_run: bool
    strategy_count: int
    active_alert_sources: tuple[str, ...]
    critical_blockers: tuple[str, ...]
    next_recommended_phase: str
    runtime_stats: dict
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "state_id": self.state_id,
            "current_mode": self.current_mode,
            "submit_permission": self.submit_permission,
            "real_submit_allowed": self.real_submit_allowed,
            "testnet_submit_allowed": self.testnet_submit_allowed,
            "dry_run_allowed": self.dry_run_allowed,
            "system_healthy": self.system_healthy,
            "dry_run": self.dry_run,
            "strategy_count": self.strategy_count,
            "active_alert_sources": list(self.active_alert_sources),
            "critical_blockers": list(self.critical_blockers),
            "next_recommended_phase": self.next_recommended_phase,
            "runtime_stats": self.runtime_stats,
            "timestamp": self.timestamp,
        }


def build_runtime_state(
    research_count: int = 0,
    shadow_signal_count: int = 0,
    shadow_ticker_count: int = 0,
    alert_count: int = 0,
    feishu_payload_count: int = 0,
    testnet_intent_count: int = 0,
    testnet_lifecycle_count: int = 0,
    no_submit_evidence_count: int = 0,
    high_risk_isolated_count: int = 10,
    blockers: list[str] | None = None,
) -> RuntimeSystemState:
    """Build runtime system state from aggregated metrics."""
    now = datetime.now(timezone.utc).isoformat()
    blockers = blockers or []

    return RuntimeSystemState(
        state_id="runtime_state_v1",
        current_mode="ACTUAL_DRY_RUN",
        submit_permission="NO_SUBMIT",
        real_submit_allowed=False,
        testnet_submit_allowed=False,
        dry_run_allowed=True,
        system_healthy=len(blockers) == 0,
        dry_run=True,
        strategy_count=11,
        active_alert_sources=(
            "earnings", "stock_price", "macd_rebound",
            "binance_futures", "system_heartbeat",
            "research_watchlist", "shadow_signals",
        ),
        critical_blockers=tuple(blockers),
        next_recommended_phase="TESTNET_DRY_RUN_SIMULATION",
        runtime_stats={
            "research_items": research_count,
            "shadow_signals": shadow_signal_count,
            "shadow_tickers": shadow_ticker_count,
            "alert_events": alert_count,
            "feishu_payloads": feishu_payload_count,
            "testnet_intents": testnet_intent_count,
            "testnet_lifecycle_events": testnet_lifecycle_count,
            "no_submit_evidence": no_submit_evidence_count,
            "high_risk_isolated": high_risk_isolated_count,
        },
        timestamp=now,
    )


def write_state(state: RuntimeSystemState, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
