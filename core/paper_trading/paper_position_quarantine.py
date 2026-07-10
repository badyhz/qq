"""Paper position quarantine — marks legacy positions for exclusion from stats.

No orders, no accounts, no secrets. Pure metadata tagging.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.paper_trading.paper_position import CLOSED_STATUSES


QUARANTINE_SAFETY_FLAGS = [
    "PAPER_ONLY",
    "SHADOW_ONLY",
    "NO_ORDER",
    "NO_REAL_ORDER",
    "NO_ACCOUNT",
    "NO_SECRET",
    "NO_TESTNET",
    "NO_LIVE",
    "READONLY_METADATA_ONLY",
]


@dataclass(frozen=True)
class QuarantineResult:
    """Result of quarantining legacy positions."""
    date: str
    source_file: str
    position_count: int
    quarantined_count: int
    clean_count: int
    excluded_from_stats_count: int
    reason_counts: dict[str, int]
    positions: list[dict[str, Any]]
    clean_summary: dict[str, Any]
    safety_flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "source_file": self.source_file,
            "position_count": self.position_count,
            "quarantined_count": self.quarantined_count,
            "clean_count": self.clean_count,
            "excluded_from_stats_count": self.excluded_from_stats_count,
            "reason_counts": dict(self.reason_counts),
            "positions": self.positions,
            "clean_summary": self.clean_summary,
            "safety_flags": list(self.safety_flags),
        }


def quarantine_positions(
    positions: list[dict[str, Any]],
    date_str: str,
    source_file: str = "",
) -> QuarantineResult:
    """Tag legacy positions for exclusion from performance stats."""
    tagged: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    quarantined = 0
    clean = 0

    for pos in positions:
        reasons = _check_legacy(pos)
        if reasons:
            for r in reasons:
                reason_counts[r] = reason_counts.get(r, 0) + 1
            pos_copy = dict(pos)
            pos_copy["quarantine_status"] = "LEGACY_PRE_FUTURE_ONLY_FIX"
            pos_copy["excluded_from_performance_stats"] = True
            pos_copy["quarantine_reasons"] = reasons
            tagged.append(pos_copy)
            quarantined += 1
        else:
            pos_copy = dict(pos)
            pos_copy["quarantine_status"] = "CLEAN"
            pos_copy["excluded_from_performance_stats"] = False
            pos_copy["quarantine_reasons"] = []
            tagged.append(pos_copy)
            clean += 1

    clean_summary = _build_clean_summary(tagged)

    return QuarantineResult(
        date=date_str,
        source_file=source_file,
        position_count=len(positions),
        quarantined_count=quarantined,
        clean_count=clean,
        excluded_from_stats_count=quarantined,
        reason_counts=reason_counts,
        positions=tagged,
        clean_summary=clean_summary,
        safety_flags=list(QUARANTINE_SAFETY_FLAGS),
    )


def evaluate_position_quarantine(pos: dict[str, Any]) -> tuple[str, list[str]]:
    """Evaluate quarantine status for a single position.

    Shared function used by quarantine runner and canonical recomputation.
    Returns: (quarantine_status, reasons)
    quarantine_status is "CLEAN" or "EXCLUDED".
    """
    reasons = _check_legacy(pos)
    if reasons:
        return "EXCLUDED", reasons
    return "CLEAN", []


def _normalize_epoch_seconds(value: Any) -> float | None:
    """Normalize epoch seconds/milliseconds/microseconds to seconds."""
    if value is None:
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    if ts > 1e15:
        return ts / 1_000_000
    if ts > 1e12:
        return ts / 1_000
    return ts


def _check_legacy(pos: dict[str, Any]) -> list[str]:
    """Check if a position is legacy. Returns list of reasons (empty = clean)."""
    reasons = []
    status = pos.get("status", "OPEN")
    lifecycle_mode = pos.get("lifecycle_mode")
    opened_bar_time = pos.get("opened_bar_time")
    last_checked_bar_time = pos.get("last_checked_bar_time")
    opened_ts = _normalize_epoch_seconds(opened_bar_time)
    last_checked_ts = _normalize_epoch_seconds(last_checked_bar_time)
    exit_reason = pos.get("exit_reason", "") or ""

    # Rule 1: closed status without future_only lifecycle
    if status in CLOSED_STATUSES and lifecycle_mode != "future_only":
        reasons.append("closed_without_future_only_lifecycle")

    # Rule 2: missing or unknown lifecycle_mode
    if lifecycle_mode is None or lifecycle_mode == "MISSING" or lifecycle_mode == "unknown":
        reasons.append("missing_lifecycle_mode")

    # Rule 3: missing opened_bar_time
    if opened_bar_time is None or opened_bar_time == "MISSING":
        reasons.append("missing_opened_bar_time")

    # Rule 4: closed but normalized last check <= open time (same-cycle update)
    if (status in CLOSED_STATUSES
            and last_checked_ts is not None and opened_ts is not None
            and last_checked_ts <= opened_ts):
        reasons.append("same_cycle_update")

    # Rule 5: exit_reason contains legacy markers
    for marker in ("old_backtest", "same_cycle", "unknown"):
        if marker in exit_reason:
            reasons.append(f"legacy_exit_reason_{marker}")

    return reasons


def _build_clean_summary(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """Build summary using only clean (non-excluded) positions."""
    clean = [p for p in positions if not p.get("excluded_from_performance_stats", False)]
    excluded = [p for p in positions if p.get("excluded_from_performance_stats", False)]

    open_count = sum(1 for p in clean if p.get("status") == "OPEN")
    tp_count = sum(1 for p in clean if p.get("status") == "TAKE_PROFIT_HIT")
    sl_count = sum(1 for p in clean if p.get("status") == "STOP_LOSS_HIT")
    timeout_count = sum(1 for p in clean if p.get("status") == "TIMEOUT_EXIT")

    total_pnl = sum(p.get("realized_pnl", 0) for p in clean)
    avg_r = 0.0
    closed = [p for p in clean if p.get("r_multiple", 0) != 0]
    if closed:
        avg_r = sum(p.get("r_multiple", 0) for p in closed) / len(closed)

    # Count legacy vs other exclusions
    legacy_excluded = sum(1 for p in excluded
                         if p.get("quarantine_status") == "LEGACY_PRE_FUTURE_ONLY_FIX")

    return {
        "clean_position_count": len(clean),
        "clean_open_count": open_count,
        "clean_take_profit_hit_count": tp_count,
        "clean_stop_loss_hit_count": sl_count,
        "clean_timeout_exit_count": timeout_count,
        "excluded_count": len(excluded),
        "legacy_excluded_count": legacy_excluded,
        "clean_total_realized_pnl": round(total_pnl, 8),
        "clean_avg_r_multiple": round(avg_r, 4),
    }
