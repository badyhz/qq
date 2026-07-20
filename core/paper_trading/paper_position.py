"""Paper position — shadow-only position from a SHADOW_READY trade intent.

No orders, no accounts, no secrets, no testnet, no live.
"""
from __future__ import annotations

import json
import os
import uuid
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


POSITION_SAFETY_FLAGS = [
    "PAPER_ONLY",
    "SHADOW_ONLY",
    "NO_ORDER",
    "NO_REAL_ORDER",
    "NO_ACCOUNT",
    "NO_SECRET",
    "NO_TESTNET",
    "NO_LIVE",
    "NO_WEBSOCKET",
    "NO_WEBHOOK_SEND",
    "POSITION_SIMULATION_ONLY",
]

CLOSED_STATUSES = {"TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT", "INVALID"}
SIGNAL_IDENTITY_SCHEMA_VERSION = "shadow_signal_v1"
EXPOSURE_IDENTITY_SCHEMA_VERSION = "shadow_exposure_v1"
OVERLAP_AUDIT_RULE_VERSION = "cross_day_exposure_v1"
OVERLAP_MANIFEST_FILENAME = "paper_position_overlap_exclusions.json"


def exposure_identity(record: dict[str, Any]) -> str:
    """Return the non-pyramiding economic exposure identity.

    An incomplete identity is unsafe: callers must fail closed rather than let an
    unidentifiable intent bypass the open-exposure guard.
    """
    parts = (
        str(record.get("strategy_id") or "").strip(),
        str(record.get("symbol") or "").strip().upper(),
        str(record.get("timeframe") or "").strip().lower(),
        str(record.get("side") or "").strip().upper(),
    )
    if not all(parts) or parts[3] not in {"LONG", "SHORT"}:
        raise ValueError("incomplete exposure identity")
    return "|".join((EXPOSURE_IDENTITY_SCHEMA_VERSION, *parts))


def stable_signal_key(intent: dict[str, Any]) -> str:
    """Build a stable, non-secret identity for one observed strategy signal.

    Newer producers may provide signal_bar_close_time.  The current legacy
    producer does not, so its compatibility reference uses only deterministic
    signal content (collection date and quoted levels), never process time,
    run id, file path, or a random UUID.
    """
    bar_time = intent.get("signal_bar_close_time")
    if bar_time is not None and str(bar_time).strip():
        ts = _normalize_timestamp_to_seconds(bar_time)
        if ts <= 0:
            raise ValueError("invalid signal_bar_close_time")
        signal_reference = datetime.fromtimestamp(ts, timezone.utc).isoformat()
        reference_type = "signal_bar_close_time"
    else:
        reference_type = "legacy_deterministic_signal_content"
        signal_reference = json.dumps({
            "date": str(intent.get("date") or ""),
            "entry_price": _normalize_fingerprint_value(intent.get("entry_price")),
            "stop_loss": _normalize_fingerprint_value(intent.get("stop_loss")),
            "take_profit": _normalize_fingerprint_value(intent.get("take_profit")),
            "source_reason": str(intent.get("source_reason") or ""),
        }, sort_keys=True, separators=(",", ":"))

    payload = {
        "schema_version": SIGNAL_IDENTITY_SCHEMA_VERSION,
        "strategy_id": str(intent.get("strategy_id") or "").strip(),
        "symbol": str(intent.get("symbol") or "").strip().upper(),
        "timeframe": str(intent.get("timeframe") or "").strip().lower(),
        "side": str(intent.get("side") or "").strip().upper(),
        "strategy_version": str(intent.get("strategy_version") or "unspecified"),
        "reference_type": reference_type,
        "signal_reference": signal_reference,
    }
    exposure_identity(intent)
    if not payload["strategy_id"] or not signal_reference:
        raise ValueError("incomplete signal identity")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class PaperPosition:
    """Shadow-only paper position. Never results in a real order."""
    position_id: str
    intent_id: str
    signal_key: str
    signal_key_schema_version: str
    date: str
    source: str
    strategy_id: str
    strategy_type: str
    symbol: str
    timeframe: str
    side: str
    status: str
    entry_price: float
    stop_loss: float
    take_profit: float
    rr_ratio: float
    position_size_preview: float
    max_risk_pct: float
    paper_equity_preview: float
    opened_at: str
    opened_bar_time: Optional[int]
    closed_at: Optional[str]
    exit_price: Optional[float]
    exit_reason: Optional[str]
    unrealized_pnl: float
    realized_pnl: float
    realized_pnl_pct: float
    r_multiple: float
    source_trade_intent_status: str
    risk_gate_status: str
    lifecycle_mode: str
    last_checked_at: Optional[str]
    last_checked_bar_time: Optional[int]
    safety_flags: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "intent_id": self.intent_id,
            "signal_key": self.signal_key,
            "signal_key_schema_version": self.signal_key_schema_version,
            "date": self.date,
            "source": self.source,
            "strategy_id": self.strategy_id,
            "strategy_type": self.strategy_type,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": self.side,
            "status": self.status,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "rr_ratio": self.rr_ratio,
            "position_size_preview": self.position_size_preview,
            "max_risk_pct": self.max_risk_pct,
            "paper_equity_preview": self.paper_equity_preview,
            "opened_at": self.opened_at,
            "opened_bar_time": self.opened_bar_time,
            "closed_at": self.closed_at,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "realized_pnl_pct": self.realized_pnl_pct,
            "r_multiple": self.r_multiple,
            "source_trade_intent_status": self.source_trade_intent_status,
            "risk_gate_status": self.risk_gate_status,
            "lifecycle_mode": self.lifecycle_mode,
            "last_checked_at": self.last_checked_at,
            "last_checked_bar_time": self.last_checked_bar_time,
            "safety_flags": list(self.safety_flags),
            "created_at": self.created_at,
        }


def open_position(intent: dict[str, Any], paper_equity: float = 10000.0) -> Optional[PaperPosition]:
    """Open a paper position from a SHADOW_READY trade intent.

    Returns None if intent is not SHADOW_READY or side is NO_TRADE.
    """
    intent_status = intent.get("intent_status")
    if intent_status != "SHADOW_READY":
        return None

    side = intent.get("side")
    if side not in ("LONG", "SHORT"):
        return None

    execution_mode = intent.get("execution_mode")
    if execution_mode != "shadow_only":
        return None

    now = datetime.now(timezone.utc).isoformat()
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    entry = float(intent.get("entry_price") or 0)
    sl = float(intent.get("stop_loss") or 0)
    tp = float(intent.get("take_profit") or 0)

    if entry <= 0 or sl <= 0 or tp <= 0:
        return None

    return PaperPosition(
        position_id=f"PP_{uuid.uuid4().hex[:12]}",
        intent_id=str(intent.get("intent_id") or ""),
        signal_key=stable_signal_key(intent),
        signal_key_schema_version=SIGNAL_IDENTITY_SCHEMA_VERSION,
        date=str(intent.get("date") or ""),
        source="trade_intent",
        strategy_id=str(intent.get("strategy_id") or ""),
        strategy_type=str(intent.get("strategy_type") or ""),
        symbol=str(intent.get("symbol") or ""),
        timeframe=str(intent.get("timeframe") or ""),
        side=side,
        status="OPEN",
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        rr_ratio=float(intent.get("rr_ratio") or 0),
        position_size_preview=float(intent.get("position_size_preview") or 0),
        max_risk_pct=float(intent.get("max_risk_pct") or 0),
        paper_equity_preview=paper_equity,
        opened_at=now,
        opened_bar_time=now_ts,
        closed_at=None,
        exit_price=None,
        exit_reason=None,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        realized_pnl_pct=0.0,
        r_multiple=0.0,
        source_trade_intent_status=intent_status,
        risk_gate_status=str(intent.get("risk_gate_status") or ""),
        lifecycle_mode="future_only",
        last_checked_at=None,
        last_checked_bar_time=None,
        safety_flags=list(POSITION_SAFETY_FLAGS),
        created_at=now,
    )


def dict_to_position(d: dict[str, Any]) -> PaperPosition:
    """Reconstruct a PaperPosition from a dict (e.g. from JSON)."""
    return PaperPosition(
        position_id=d["position_id"],
        intent_id=d["intent_id"],
        signal_key=str(d.get("signal_key") or ""),
        signal_key_schema_version=str(d.get("signal_key_schema_version") or "legacy_missing"),
        date=d["date"],
        source=d["source"],
        strategy_id=d["strategy_id"],
        strategy_type=d["strategy_type"],
        symbol=d["symbol"],
        timeframe=d["timeframe"],
        side=d["side"],
        status=d["status"],
        entry_price=d["entry_price"],
        stop_loss=d["stop_loss"],
        take_profit=d["take_profit"],
        rr_ratio=d["rr_ratio"],
        position_size_preview=d["position_size_preview"],
        max_risk_pct=d["max_risk_pct"],
        paper_equity_preview=d["paper_equity_preview"],
        opened_at=d["opened_at"],
        opened_bar_time=d.get("opened_bar_time"),
        closed_at=d.get("closed_at"),
        exit_price=d.get("exit_price"),
        exit_reason=d.get("exit_reason"),
        unrealized_pnl=d.get("unrealized_pnl", 0.0),
        realized_pnl=d.get("realized_pnl", 0.0),
        realized_pnl_pct=d.get("realized_pnl_pct", 0.0),
        r_multiple=d.get("r_multiple", 0.0),
        source_trade_intent_status=d.get("source_trade_intent_status", ""),
        risk_gate_status=d.get("risk_gate_status", ""),
        lifecycle_mode=d.get("lifecycle_mode", "future_only"),
        last_checked_at=d.get("last_checked_at"),
        last_checked_bar_time=d.get("last_checked_bar_time"),
        safety_flags=d.get("safety_flags", list(POSITION_SAFETY_FLAGS)),
        created_at=d.get("created_at", ""),
    )


TERMINAL_STATUSES = {"TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT", "INVALID"}


@dataclass(frozen=True)
class PositionSelection:
    """Result of canonical state selection between two records for the same position."""
    selected: dict
    decision: str  # "keep_old", "use_new", "conflict_terminal"
    conflict: bool
    conflict_reason: str | None


def select_canonical_position_state(
    old: dict[str, Any],
    new: dict[str, Any],
) -> PositionSelection:
    """Select canonical state between two records for the same position_id.

    Rules:
    - OPEN → OPEN: newer timestamp wins
    - OPEN → CLOSED: select CLOSED
    - CLOSED → OPEN: keep CLOSED (terminal irreversible)
    - CLOSED → same CLOSED: keep old if only observation fields differ
    - CLOSED → different CLOSED: conflict (terminal state changed)
    """
    old_status = old.get("status")
    new_status = new.get("status")
    old_terminal = _is_terminal_status(old_status)
    new_terminal = _is_terminal_status(new_status)

    # Both non-terminal: newer timestamp wins
    if not old_terminal and not new_terminal:
        old_ts = _position_sort_ts(old)
        new_ts = _position_sort_ts(new)
        if new_ts > old_ts:
            return PositionSelection(new, "use_new", False, None)
        return PositionSelection(old, "keep_old", False, None)

    # OPEN → CLOSED: select CLOSED
    if not old_terminal and new_terminal:
        return PositionSelection(new, "use_new", False, None)

    # CLOSED → OPEN: keep CLOSED, terminal is irreversible
    if old_terminal and not new_terminal:
        return PositionSelection(old, "keep_old", True, "terminal_irreversible")

    # Both terminal
    if old_status == new_status:
        # Same terminal status: check if only observation fields changed
        if position_state_fingerprint(old) == position_state_fingerprint(new):
            return PositionSelection(old, "keep_old", False, None)
        # Meaningful change within same status: keep first (trustworthy)
        return PositionSelection(old, "keep_old", True, "terminal_field_change")

    # Different terminal statuses: CONFLICT
    return PositionSelection(
        old, "conflict_terminal", True,
        f"terminal_conflict: {old_status} vs {new_status}",
    )

# Source whitelist — only these are eligible for canonical counting
ELIGIBLE_SOURCES = frozenset({
    "real_public_readonly",
    "real_public_http",
    "public_readonly_update",
    "trade_intent",  # production paper position source
    "",  # legacy records without source treated as eligible only if other proof exists
})

INELIGIBLE_SOURCES = frozenset({
    "offline_sample",
    "offline",
    "replay",
    "test_fixture",
    "test",
    "mock",
})


def _position_dedupe_key(rec: dict[str, Any]) -> str | None:
    """Build a stable deduplication key for a position record.

    Returns None if position_id is missing — such records are excluded from canonical.
    """
    pid = str(rec.get("position_id") or "").strip()
    if pid:
        return f"pid:{pid}"
    return None  # missing position_id → excluded


def _normalize_timestamp_to_seconds(val: Any) -> float:
    """Normalize a timestamp value to seconds.

    Handles:
    - ISO 8601 strings
    - 10-digit (seconds)
    - 13-digit (milliseconds)
    - 16-digit (microseconds)
    - 19-digit (nanoseconds)
    Returns 0.0 if unparseable.
    """
    if val is None:
        return 0.0
    if isinstance(val, str) and "T" in val:
        try:
            from datetime import datetime as _dt
            return _dt.fromisoformat(val.replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError, OSError):
            return 0.0
    try:
        fval = float(val)
    except (ValueError, TypeError):
        return 0.0
    if fval <= 0:
        return 0.0
    # Auto-detect unit by digit count
    if fval > 1e18:      # nanoseconds
        return fval / 1e9
    if fval > 1e15:      # microseconds
        return fval / 1e6
    if fval > 1e12:      # milliseconds
        return fval / 1e3
    return fval           # seconds


def _position_sort_ts(rec: dict[str, Any]) -> float:
    """Extract a sortable timestamp from a position record.

    Priority: recorded_at > closed_at > last_checked_at > opened_at > created_at.
    All values normalized to seconds.
    Returns 0 if none available.
    """
    for field in (
        "recorded_at", "closed_at", "last_checked_at", "last_checked_bar_time",
        "opened_at", "created_at",
    ):
        val = rec.get(field)
        ts = _normalize_timestamp_to_seconds(val)
        if ts > 0:
            return ts
    return 0.0


def _is_terminal_status(status: str | None) -> bool:
    """Check if a status is terminal (closed)."""
    return status in TERMINAL_STATUSES


def _should_replace(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """Decide whether new record should replace old for the same dedup key.

    Rules (terminal state is irreversible):
    1. If old is terminal and new is non-terminal: NEVER replace.
    2. Higher timestamp wins.
    3. If timestamps equal: terminal status beats non-terminal.
    4. If both terminal or both non-terminal: keep existing (first seen wins).
    """
    old_terminal = _is_terminal_status(old.get("status"))
    new_terminal = _is_terminal_status(new.get("status"))

    # Terminal state is irreversible: CLOSED cannot be overwritten by OPEN
    if old_terminal and not new_terminal:
        return False

    old_ts = _position_sort_ts(old)
    new_ts = _position_sort_ts(new)
    if new_ts > old_ts:
        return True
    if new_ts < old_ts:
        return False
    # Equal timestamp: terminal beats non-terminal
    if new_terminal and not old_terminal:
        return True
    return False  # keep existing


def _is_finite_number(value: Any) -> bool:
    """Check if value is a finite number (not NaN, Inf, or non-numeric)."""
    import math
    if value is None:
        return False
    if isinstance(value, (int,)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    try:
        from decimal import Decimal
        d = Decimal(str(value))
        return d.is_finite()
    except (ValueError, TypeError, ArithmeticError):
        return False


def _normalize_fingerprint_value(value: Any) -> str:
    """Normalize a value for stable fingerprinting.

    Numeric values: 100, 100.0, 100.00, Decimal("100.000") all produce "100".
    Non-finite values: NaN, +Inf, -Inf produce canonical labels.
    -0.0 normalizes to 0.
    Other values: str() as-is.
    """
    import math

    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return "NON_FINITE_NAN"
        if math.isinf(value):
            return "NON_FINITE_POS_INF" if value > 0 else "NON_FINITE_NEG_INF"
        # Normalize -0.0 to 0
        if value == 0:
            return "0"
        if value == int(value):
            return str(int(value))
        return str(value)
    if isinstance(value, int):
        return str(value)
    try:
        from decimal import Decimal
        d = Decimal(str(value))
        if not d.is_finite():
            if d.is_nan():
                return "NON_FINITE_NAN"
            return "NON_FINITE_POS_INF" if d > 0 else "NON_FINITE_NEG_INF"
        normalized = d.normalize()
        if normalized == 0:
            return "0"
        if normalized == int(normalized):
            return str(int(normalized))
        return str(normalized)
    except (ValueError, TypeError, ArithmeticError):
        return str(value)


def position_state_fingerprint(rec: dict[str, Any]) -> str:
    """Compute a stable fingerprint of a position's meaningful state.

    Used for idempotent ledger writes — if the fingerprint hasn't changed,
    don't append a new line.

    Excludes observation-only fields (last_checked_at, recorded_at, generated_at,
    updated_at) to avoid duplicate appends when only check time changes.
    Numeric fields are normalized so 100 == 100.0 == 100.00.
    """
    import hashlib
    parts = [
        str(rec.get("position_id", "")),
        str(rec.get("status", "")),
        _normalize_fingerprint_value(rec.get("entry_price")),
        _normalize_fingerprint_value(rec.get("exit_price")),
        str(rec.get("exit_reason", "")),
        _normalize_fingerprint_value(rec.get("stop_loss")),
        _normalize_fingerprint_value(rec.get("take_profit")),
        _normalize_fingerprint_value(rec.get("r_multiple")),
        str(rec.get("closed_at", "")),
        str(rec.get("quarantine_status", "")),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def load_canonical_positions(
    report_dir: str,
    date_glob: str = "*",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load all positions from all daily ledger files, deduped by position_id.

    Returns the latest state for each unique position, sorted by position_id,
    plus diagnostic metadata.

    Args:
        report_dir: Directory containing {date}_paper_position_ledger.jsonl files.
        date_glob: Glob pattern for date prefix (default "*" = all dates).

    Returns:
        Tuple of (positions list, diagnostics dict).
        positions: latest state per unique position_id (sorted).
        diagnostics: raw_count, excluded_no_position_id, error, etc.
    """
    import glob as _glob

    latest_by_key: dict[str, dict[str, Any]] = {}
    diagnostics: dict[str, Any] = {
        "raw_count": 0,
        "excluded_no_position_id": 0,
        "files_read": 0,
        "files_error": 0,
        "load_error": None,
        "corrupted_lines": 0,
        "terminal_conflicts": [],
        "terminal_conflict_count": 0,
    }

    pattern = os.path.join(report_dir, f"{date_glob}_paper_position_ledger.jsonl")
    for path in sorted(_glob.glob(pattern)):
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    diagnostics["raw_count"] += 1
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        diagnostics["corrupted_lines"] += 1
                        continue
                    key = _position_dedupe_key(rec)
                    if key is None:
                        diagnostics["excluded_no_position_id"] += 1
                        continue
                    old = latest_by_key.get(key, {})
                    if not old:
                        latest_by_key[key] = rec
                    else:
                        sel = select_canonical_position_state(old, rec)
                        latest_by_key[key] = sel.selected
                        if sel.conflict:
                            conflict_type = "terminal_status_conflict"
                            fatal = True
                            if sel.conflict_reason == "terminal_irreversible":
                                conflict_type = "terminal_regression"
                                fatal = False
                            elif sel.conflict_reason == "terminal_field_change":
                                conflict_type = "terminal_field_change"
                                fatal = True
                            diagnostics["terminal_conflicts"].append({
                                "position_id": rec.get("position_id"),
                                "conflict_type": conflict_type,
                                "old_status": old.get("status"),
                                "new_status": rec.get("status"),
                                "old_ts": old.get("recorded_at") or old.get("closed_at", ""),
                                "new_ts": rec.get("recorded_at") or rec.get("closed_at", ""),
                                "reason": sel.conflict_reason,
                                "fatal": fatal,
                            })
                            diagnostics["terminal_conflict_count"] += 1
            diagnostics["files_read"] += 1
        except OSError as e:
            diagnostics["files_error"] += 1
            diagnostics["load_error"] = str(e)
            continue

    positions = sorted(latest_by_key.values(), key=lambda r: str(r.get("position_id", "")))
    return positions, diagnostics


def build_overlap_exclusion_manifest(
    canonical_positions: list[dict[str, Any]],
    trusted_cohort_start_at: str,
) -> dict[str, Any]:
    """Identify later positions opened while the same exposure was still OPEN.

    The canonical ledger is read only.  The later opening is excluded; the
    earliest still-open position remains the reference exposure.
    """
    cohort_ts = _normalize_timestamp_to_seconds(trusted_cohort_start_at)
    if cohort_ts <= 0:
        raise ValueError("trusted_cohort_start_at must be a timezone-aware timestamp")

    ordered: list[tuple[float, str, dict[str, Any]]] = []
    for position in canonical_positions:
        opened_ts = _normalize_timestamp_to_seconds(position.get("opened_at"))
        pid = str(position.get("position_id") or "").strip()
        if opened_ts <= 0 or not pid:
            raise ValueError(f"position {pid or '<missing>'} has no valid opened_at")
        exposure_identity(position)
        ordered.append((opened_ts, pid, position))
    ordered.sort(key=lambda item: (item[0], item[1]))

    active: dict[str, list[dict[str, Any]]] = {}
    exclusions: list[dict[str, Any]] = []
    for opened_ts, _pid, position in ordered:
        key = exposure_identity(position)
        still_active = []
        for prior in active.get(key, []):
            prior_closed_ts = _normalize_timestamp_to_seconds(prior.get("closed_at"))
            if prior_closed_ts <= 0 or prior_closed_ts > opened_ts:
                still_active.append(prior)
        if still_active:
            existing = min(
                still_active,
                key=lambda item: (
                    _normalize_timestamp_to_seconds(item.get("opened_at")),
                    str(item.get("position_id") or ""),
                ),
            )
            exclusions.append({
                "position_id": position.get("position_id"),
                "exclusion_reason": "overlapping_open_exposure",
                "overlaps_with_position_id": existing.get("position_id"),
                "strategy": position.get("strategy_id"),
                "symbol": position.get("symbol"),
                "timeframe": position.get("timeframe"),
                "side": position.get("side"),
                "opened_at": position.get("opened_at"),
                "existing_position_opened_at": existing.get("opened_at"),
                "existing_position_closed_at": existing.get("closed_at"),
                "audit_rule_version": OVERLAP_AUDIT_RULE_VERSION,
                "excluded_at": trusted_cohort_start_at,
                "source": "independent_audit_remediation",
            })
        still_active.append(position)
        active[key] = still_active

    return {
        "schema_version": 1,
        "audit_rule_version": OVERLAP_AUDIT_RULE_VERSION,
        "trusted_cohort_start_at": trusted_cohort_start_at,
        "trusted_cohort_rule_version": OVERLAP_AUDIT_RULE_VERSION,
        "raw_canonical_positions": len(canonical_positions),
        "excluded_overlap_positions": len(exclusions),
        "exclusions": exclusions,
    }


def load_overlap_exclusion_manifest(report_dir: str) -> dict[str, Any] | None:
    """Load and validate the fixed legacy overlap exclusion manifest."""
    path = os.path.join(report_dir, OVERLAP_MANIFEST_FILENAME)
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        manifest = json.load(f)
    if manifest.get("audit_rule_version") != OVERLAP_AUDIT_RULE_VERSION:
        raise ValueError("unsupported overlap exclusion audit rule")
    if not isinstance(manifest.get("exclusions"), list):
        raise ValueError("overlap exclusion manifest has no exclusions list")
    if _normalize_timestamp_to_seconds(manifest.get("trusted_cohort_start_at")) <= 0:
        raise ValueError("overlap exclusion manifest has invalid trusted cohort start")
    ids = [str(item.get("position_id") or "") for item in manifest["exclusions"]]
    if any(not pid for pid in ids) or len(ids) != len(set(ids)):
        raise ValueError("overlap exclusion manifest has missing or duplicate position ids")
    return manifest


def load_canonical_closed_clean_positions(
    report_dir: str,
    strict: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Unified canonical entry point for Scorecard, Gate, Registry, and audit.

    Returns:
        Tuple of (eligible_positions, all_canonical_positions, diagnostics).
        eligible_positions: CLOSED positions passing all eligibility checks.
        all_canonical_positions: all canonical positions (deduped).
        diagnostics: comprehensive diagnostic metadata.

    diagnostics includes:
        raw_records, unique_positions, closed_positions, eligible_closed_clean,
        explicit_clean, derived_clean, exclusions (business), fatal_errors (technical),
        missing_position_id, files_read, files_error, accounting_status
    """
    # Load all canonical positions
    all_positions, load_diag = load_canonical_positions(report_dir)

    # Load lifecycle metadata and the fixed legacy-overlap exclusion set.
    lifecycle_metadata = _load_lifecycle_metadata(report_dir)
    overlap_manifest = None
    overlap_manifest_error = None
    try:
        overlap_manifest = load_overlap_exclusion_manifest(report_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        overlap_manifest_error = str(exc)
    overlap_ids = {
        str(item.get("position_id"))
        for item in (overlap_manifest or {}).get("exclusions", [])
    }
    trusted_cohort_start_at = (overlap_manifest or {}).get("trusted_cohort_start_at")
    trusted_cohort_start_ts = _normalize_timestamp_to_seconds(trusted_cohort_start_at)

    # Evaluate eligibility for each position
    eligible_positions = []
    closed_positions = []
    explicit_clean = 0
    derived_clean = 0
    exclusions = {
        "total": 0,
        "quarantine_excluded": 0,
        "quarantine_unverifiable": 0,
        "source_ineligible": 0,
        "source_unknown": 0,
        "overlapping_open_exposure": 0,
        "open": 0,
        "invalid": 0,
    }
    fatal_errors = []

    for p in all_positions:
        # Check if CLOSED
        status = p.get("status")
        is_closed = status in ("TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT")
        if is_closed:
            closed_positions.append(p)
        else:
            # OPEN positions are business exclusions
            exclusions["open"] += 1
            exclusions["total"] += 1
            continue

        if str(p.get("position_id") or "") in overlap_ids:
            exclusions["overlapping_open_exposure"] += 1
            exclusions["total"] += 1
            continue

        # Evaluate eligibility
        eligibility = evaluate_canonical_eligibility(p, lifecycle_metadata)

        # Track quarantine stats
        if eligibility.quarantine_source == "explicit":
            if eligibility.quarantine_status == "CLEAN":
                explicit_clean += 1
        elif eligibility.quarantine_source == "recomputed_legacy":
            if eligibility.quarantine_status == "CLEAN":
                derived_clean += 1

        # Track business exclusions (not fatal errors)
        if not eligibility.eligible:
            exclusions["total"] += 1
            reason = eligibility.exclusion_reason or ""
            if "quarantine_excluded" in reason:
                exclusions["quarantine_excluded"] += 1
            elif "quarantine_unverifiable" in reason:
                exclusions["quarantine_unverifiable"] += 1
            elif "source_ineligible" in reason:
                exclusions["source_ineligible"] += 1
            elif "source_unknown" in reason:
                exclusions["source_unknown"] += 1
            continue

        # Check for non-finite values in accounting-critical fields
        has_non_finite = False
        for field in ("entry_price", "exit_price", "stop_loss", "take_profit", "r_multiple"):
            val = p.get(field)
            if val is not None and not _is_finite_number(val):
                has_non_finite = True
                fatal_errors.append(
                    f"Non-finite value in {p.get('position_id')}.{field}: {val}"
                )
                break

        # Additional CLOSED-specific validation
        if not has_non_finite and (
            p.get("lifecycle_mode") == "future_only" and
            p.get("entry_price") and p.get("exit_price") is not None and
            p.get("r_multiple") is not None and p.get("closed_at")):
            eligible_positions.append(p)

    # Terminal conflicts: fatal for status/field changes, non-fatal for regressions
    terminal_conflicts = load_diag.get("terminal_conflicts", [])
    terminal_regressions = []
    if terminal_conflicts:
        for tc in terminal_conflicts:
            if tc.get("fatal", True):
                fatal_errors.append(
                    f"Terminal conflict ({tc.get('conflict_type', 'unknown')}): "
                    f"{tc['position_id']} {tc['old_status']} vs {tc['new_status']}"
                )
            else:
                terminal_regressions.append(tc)

    # Determine fatal errors (technical issues that block Gate/Scorecard)
    if load_diag.get("load_error"):
        fatal_errors.append(f"Load error: {load_diag['load_error']}")
    if load_diag.get("files_error", 0) > 0:
        fatal_errors.append(f"File errors: {load_diag['files_error']} files failed")
    if load_diag.get("corrupted_lines", 0) > 0:
        fatal_errors.append(f"Corrupted lines: {load_diag['corrupted_lines']}")
    if overlap_manifest_error:
        fatal_errors.append(f"Overlap exclusion manifest error: {overlap_manifest_error}")

    accounting_status = "ERROR" if fatal_errors else "OK"

    # Build comprehensive diagnostics
    diagnostics = {
        "raw_records": load_diag.get("raw_count", 0),
        "unique_positions": len(all_positions),
        "closed_positions": len(closed_positions),
        "eligible_closed_clean": len(eligible_positions),
        "raw_canonical_closed": len(closed_positions),
        "excluded_overlap_closed": exclusions["overlapping_open_exposure"],
        "eligible_legacy_closed": sum(
            1 for p in eligible_positions
            if trusted_cohort_start_ts <= 0
            or _normalize_timestamp_to_seconds(p.get("opened_at")) < trusted_cohort_start_ts
        ),
        "trusted_cohort_closed": sum(
            1 for p in eligible_positions
            if trusted_cohort_start_ts > 0
            and _normalize_timestamp_to_seconds(p.get("opened_at")) >= trusted_cohort_start_ts
        ),
        "trusted_cohort_start_at": trusted_cohort_start_at,
        "trusted_cohort_rule_version": (overlap_manifest or {}).get("trusted_cohort_rule_version"),
        "explicit_clean": explicit_clean,
        "derived_clean": derived_clean,
        "exclusions": exclusions,
        "fatal_errors": fatal_errors,
        "terminal_conflicts": terminal_conflicts,
        "terminal_conflict_count": load_diag.get("terminal_conflict_count", 0),
        "terminal_regressions": terminal_regressions,
        "missing_position_id": load_diag.get("excluded_no_position_id", 0),
        "files_read": load_diag.get("files_read", 0),
        "files_error": load_diag.get("files_error", 0),
        "corrupted_lines": load_diag.get("corrupted_lines", 0),
        "accounting_status": accounting_status,
    }

    return eligible_positions, all_positions, diagnostics


def _load_lifecycle_metadata(report_dir: str) -> dict[str, Any]:
    """Load lifecycle metadata for source verification.

    Looks for {date}_shadow_lifecycle_result.json files.
    Returns dict mapping date to lifecycle metadata.
    """
    import glob as _glob

    metadata = {}
    pattern = os.path.join(report_dir, "*_shadow_lifecycle_result.json")
    for path in sorted(_glob.glob(pattern)):
        try:
            with open(path) as f:
                data = json.load(f)
            date = data.get("date")
            if date:
                metadata[date] = {
                    "mode": data.get("mode"),
                    "safety_flags": data.get("safety_flags", []),
                    "allow_public_http": data.get("allow_public_http", False),
                }
        except (OSError, json.JSONDecodeError):
            continue

    return metadata


def classify_quarantine_status(p: dict[str, Any]) -> str:
    """Classify a position's quarantine status.

    Returns: "CLEAN", "EXCLUDED", or "UNKNOWN".
    Missing quarantine_status is "UNKNOWN", not "CLEAN".
    """
    qs = p.get("quarantine_status")
    if qs == "CLEAN":
        return "CLEAN"
    if qs == "EXCLUDED":
        return "EXCLUDED"
    return "UNKNOWN"


def _recompute_legacy_quarantine(p: dict[str, Any]) -> tuple[str, str]:
    """Recompute quarantine status for legacy data missing the field.

    Uses shared rules from paper_position_quarantine.py.
    Returns: (quarantine_status, quarantine_source).
    quarantine_source is "explicit", "recomputed_legacy", or "unverifiable".
    """
    qs = p.get("quarantine_status")
    if qs == "CLEAN":
        return "CLEAN", "explicit"
    if qs == "EXCLUDED":
        return "EXCLUDED", "explicit"

    # UNKNOWN/None: use shared quarantine rules
    from core.paper_trading.paper_position_quarantine import evaluate_position_quarantine
    status, reasons = evaluate_position_quarantine(p)
    if status == "CLEAN":
        return "CLEAN", "recomputed_legacy"
    elif status == "EXCLUDED":
        return "EXCLUDED", "recomputed_legacy"

    # Cannot verify → UNKNOWN
    return "UNKNOWN", "unverifiable"


def classify_source_eligibility(
    p: dict[str, Any],
    lifecycle_metadata: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Classify a position's source eligibility.

    Returns: (eligible: str, reason: str).
    eligible is "ELIGIBLE", "INELIGIBLE", or "UNKNOWN".

    For trade_intent source, requires lifecycle metadata proof:
    - mode is real_public_readonly/real_public_http/public_readonly_update
    - safety_flags contains PAPER_ONLY and SHADOW_ONLY
    - not offline_sample/replay/test
    """
    source = str(p.get("source_mode") or p.get("source") or "").strip()

    # Direct ineligible sources
    if source in INELIGIBLE_SOURCES:
        return "INELIGIBLE", f"source={source}"

    # Direct eligible sources (real production sources)
    DIRECT_ELIGIBLE = {"real_public_readonly", "real_public_http", "public_readonly_update"}
    if source in DIRECT_ELIGIBLE:
        return "ELIGIBLE", f"source={source}"

    # trade_intent requires metadata proof
    if source == "trade_intent":
        if lifecycle_metadata is None:
            return "UNKNOWN", "source=trade_intent, no_metadata"
        return _verify_trade_intent_source(lifecycle_metadata)

    # Empty/missing source requires metadata proof
    if not source:
        if lifecycle_metadata is None:
            return "UNKNOWN", "source=missing, no_metadata"
        return _verify_trade_intent_source(lifecycle_metadata)

    # Unknown source
    return "UNKNOWN", f"source={source}"


def _verify_trade_intent_source(metadata: dict[str, Any]) -> tuple[str, str]:
    """Verify trade_intent source using lifecycle metadata.

    Returns: (eligible: str, reason: str).
    """
    mode = str(metadata.get("mode") or "").strip()
    safety_flags = metadata.get("safety_flags", [])

    # Check mode is real production mode
    SAFE_MODES = {"real_public_readonly", "real_public_http", "public_readonly_update"}
    if mode not in SAFE_MODES:
        return "INELIGIBLE", f"mode={mode}"

    # Check safety flags
    required_flags = {"PAPER_ONLY", "SHADOW_ONLY"}
    if not required_flags.issubset(set(safety_flags)):
        return "INELIGIBLE", "missing_safety_flags"

    # Check not offline/replay/test
    if mode in {"offline_sample", "offline", "replay", "test"}:
        return "INELIGIBLE", f"mode={mode}"

    return "ELIGIBLE", f"verified_via_lifecycle, mode={mode}"


@dataclass(frozen=True)
class PositionEligibility:
    """Result of position eligibility evaluation."""
    position_id: str
    eligible: bool
    quarantine_status: str
    quarantine_source: str
    source_status: str
    exclusion_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "eligible": self.eligible,
            "quarantine_status": self.quarantine_status,
            "quarantine_source": self.quarantine_source,
            "source_status": self.source_status,
            "exclusion_reason": self.exclusion_reason,
        }


def evaluate_canonical_eligibility(
    position: dict[str, Any],
    lifecycle_metadata: dict[str, Any] | None = None,
) -> PositionEligibility:
    """Evaluate a position's eligibility for canonical counting.

    This is the SINGLE shared function used by Scorecard, Gate, Registry, and audit.
    Returns PositionEligibility with all classification details.

    lifecycle_metadata is a dict mapping date to metadata (from _load_lifecycle_metadata).
    """
    pid = str(position.get("position_id") or "unknown")

    # Check quarantine
    qs, qs_source = _recompute_legacy_quarantine(position)

    # Get metadata for this position's date
    position_date = position.get("date")
    date_metadata = None
    if lifecycle_metadata and position_date:
        date_metadata = lifecycle_metadata.get(position_date)

    # Check source
    source_status, source_reason = classify_source_eligibility(position, date_metadata)

    # Determine eligibility
    eligible = True
    exclusion_reason = None

    # Quarantine check
    if qs == "EXCLUDED":
        eligible = False
        exclusion_reason = "quarantine_excluded"
    elif qs == "UNKNOWN":
        eligible = False
        exclusion_reason = "quarantine_unverifiable"

    # Source check (only if not already excluded)
    if eligible and source_status != "ELIGIBLE":
        eligible = False
        exclusion_reason = f"source_{source_status.lower()}: {source_reason}"

    return PositionEligibility(
        position_id=pid,
        eligible=eligible,
        quarantine_status=qs,
        quarantine_source=qs_source,
        source_status=source_status,
        exclusion_reason=exclusion_reason,
    )


def filter_canonical_closed_clean(
    positions: list[dict[str, Any]],
    lifecycle_metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Filter canonical positions to CLOSED + CLEAN + eligible only.

    Uses evaluate_canonical_eligibility for consistent filtering.
    """
    result = []
    for p in positions:
        # Basic CLOSED validation
        status = p.get("status")
        if status not in ("TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT"):
            continue
        if p.get("lifecycle_mode") != "future_only":
            continue
        if not p.get("entry_price"):
            continue
        if not p.get("exit_price"):
            continue
        if p.get("r_multiple") is None:
            continue
        if not p.get("closed_at"):
            continue

        # Use shared eligibility function
        eligibility = evaluate_canonical_eligibility(p, lifecycle_metadata)
        if eligibility.eligible:
            result.append(p)
    return result
