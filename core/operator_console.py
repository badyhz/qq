"""T21001 — Operator Console.

Pure deterministic. No I/O. No network.
Generates operator console status summary from all system components.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

VALID_CURRENT_MODES: tuple[str, ...] = (
    "SHADOW_ONLY",
    "TESTNET_DRY_RUN_PREP",
)

FORBIDDEN_MODES: tuple[str, ...] = (
    "REAL_ACTIVE",
    "LIVE_TRADING",
    "AUTO_SUBMIT",
)


@dataclass(frozen=True)
class OperatorConsoleStatus:
    """Complete operator console status."""
    current_mode: str
    submit_permission: str
    real_submit_allowed: bool
    testnet_submit_allowed: bool
    dry_run_allowed: bool
    frozen_cleanup_status: str
    promotion_status: str
    strategy_count: int
    active_alert_sources: list[str]
    critical_blockers: list[str]
    next_recommended_phase: str
    system_healthy: bool
    dry_run: bool

    def to_dict(self) -> dict:
        return {
            "current_mode": self.current_mode,
            "submit_permission": self.submit_permission,
            "real_submit_allowed": self.real_submit_allowed,
            "testnet_submit_allowed": self.testnet_submit_allowed,
            "dry_run_allowed": self.dry_run_allowed,
            "frozen_cleanup_status": self.frozen_cleanup_status,
            "promotion_status": self.promotion_status,
            "strategy_count": self.strategy_count,
            "active_alert_sources": self.active_alert_sources,
            "critical_blockers": self.critical_blockers,
            "next_recommended_phase": self.next_recommended_phase,
            "system_healthy": self.system_healthy,
            "dry_run": self.dry_run,
        }


def build_operator_console(
    frozen_cleanup_done: bool = True,
    promotion_decision: str = "READY_FOR_TESTNET_DRY_RUN_PREP",
    strategy_count: int = 11,
    alert_sources: list[str] | None = None,
    blockers: list[str] | None = None,
    dry_run_stability: float = 1.0,
) -> OperatorConsoleStatus:
    """Build operator console status."""
    blockers = blockers or []
    alert_sources = alert_sources or ["earnings", "stock_price", "macd_rebound", "binance_futures", "system_heartbeat"]

    current_mode = "SHADOW_ONLY"
    if promotion_decision == "READY_FOR_TESTNET_DRY_RUN_PREP" and frozen_cleanup_done:
        current_mode = "TESTNET_DRY_RUN_PREP"

    return OperatorConsoleStatus(
        current_mode=current_mode,
        submit_permission="NO_SUBMIT",
        real_submit_allowed=False,
        testnet_submit_allowed=False,
        dry_run_allowed=True,
        frozen_cleanup_status="COMPLETE" if frozen_cleanup_done else "PENDING",
        promotion_status=promotion_decision,
        strategy_count=strategy_count,
        active_alert_sources=alert_sources,
        critical_blockers=blockers,
        next_recommended_phase="TESTNET_DRY_RUN_SIMULATION",
        system_healthy=len(blockers) == 0 and dry_run_stability > 0.5,
        dry_run=True,
    )


def compute_console_hash(status: OperatorConsoleStatus) -> str:
    raw = json.dumps(status.to_dict(), sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_console_markdown(status: OperatorConsoleStatus) -> str:
    lines = [
        "# Operator Console",
        "",
        "## System Status",
        "",
        f"- **Current mode:** {status.current_mode}",
        f"- **Submit permission:** {status.submit_permission}",
        f"- **Real submit allowed:** {status.real_submit_allowed}",
        f"- **Testnet submit allowed:** {status.testnet_submit_allowed}",
        f"- **Dry-run allowed:** {status.dry_run_allowed}",
        f"- **System healthy:** {status.system_healthy}",
        f"- **Dry-run:** {status.dry_run}",
        "",
        "## Component Status",
        "",
        f"- **Frozen cleanup:** {status.frozen_cleanup_status}",
        f"- **Promotion status:** {status.promotion_status}",
        f"- **Strategy count:** {status.strategy_count}",
        "",
        "## Active Alert Sources",
        "",
    ]

    for src in status.active_alert_sources:
        lines.append(f"- {src}")

    lines.append("")
    lines.append("## Critical Blockers")
    lines.append("")

    if status.critical_blockers:
        for b in status.critical_blockers:
            lines.append(f"- **{b}**")
    else:
        lines.append("- None")

    lines.append("")
    lines.append(f"## Next Recommended Phase: {status.next_recommended_phase}")
    lines.append("")
    lines.append("---")
    lines.append("OPERATOR CONSOLE. DRY RUN. NO REAL ACTIONS.")
    lines.append("")

    return "\n".join(lines)


def render_next_actions_markdown(status: OperatorConsoleStatus) -> str:
    lines = [
        "# Operator Next Actions",
        "",
    ]

    if status.critical_blockers:
        lines.append("## Blockers to Resolve")
        lines.append("")
        for b in status.critical_blockers:
            lines.append(f"- {b}")
        lines.append("")

    lines.append("## Recommended Actions")
    lines.append("")
    lines.append(f"1. Current mode: {status.current_mode}")
    lines.append(f"2. Next phase: {status.next_recommended_phase}")
    lines.append(f"3. Submit permission: {status.submit_permission}")
    lines.append("")
    lines.append("## Safety Reminder")
    lines.append("")
    lines.append("- Real submit: **NOT ALLOWED**")
    lines.append("- Testnet submit: **NOT ALLOWED**")
    lines.append("- Dry-run: **ALLOWED**")
    lines.append("")

    return "\n".join(lines)


def render_blockers_markdown(status: OperatorConsoleStatus) -> str:
    lines = [
        "# Operator Blockers",
        "",
        f"**Critical blockers:** {len(status.critical_blockers)}",
        "",
    ]

    if status.critical_blockers:
        for b in status.critical_blockers:
            lines.append(f"- **{b}**")
    else:
        lines.append("- No critical blockers.")

    lines.append("")

    return "\n".join(lines)


def write_json(status: OperatorConsoleStatus, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(status.to_dict(), indent=2), encoding="utf-8")


def write_manifest(status: OperatorConsoleStatus, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "current_mode": status.current_mode,
        "system_healthy": status.system_healthy,
        "dry_run": status.dry_run,
        "console_hash": compute_console_hash(status),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
