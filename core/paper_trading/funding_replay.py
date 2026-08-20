"""Idempotent terminal-position funding evidence replay for P1-03.

This module never re-simulates a terminal position and never changes economic
facts. It only allows public funding evidence to mature from PARTIAL to COMPLETE
after a post-close funding event becomes observable.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from core.paper_trading.data_source import (
    _FIXED_INTERVAL_SECONDS,
    format_utc_timestamp,
    parse_aware_utc,
)
from core.paper_trading.paper_position import CLOSED_STATUSES, position_state_fingerprint
from core.paper_trading.paper_position_simulator import enrich_closed_position_funding

FUNDING_REPLAY_VERSION = "closed_funding_replay_v1"
MAX_FUNDING_REPLAY_LOOKBACK_SECONDS = 120 * 86400
FUNDING_LOOKBACK_CUSHION_SECONDS = 86400


def _epoch_seconds(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    if number > 1e18:
        number /= 1e9
    elif number > 1e15:
        number /= 1e6
    elif number > 1e12:
        number /= 1e3
    return number


def resolve_position_funding_close_boundary(
    position: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Resolve a deterministic historical close boundary without using now()."""
    if position.get("status") not in CLOSED_STATUSES:
        return None, None

    persisted = position.get("funding_attribution_close_time")
    if persisted:
        try:
            return (
                format_utc_timestamp(
                    parse_aware_utc(str(persisted), "funding_attribution_close_time")
                ),
                str(
                    position.get("funding_attribution_close_source")
                    or "persisted_funding_boundary_v1"
                ),
            )
        except ValueError:
            return None, None

    if (
        position.get("status") == "STOP_LOSS_HIT"
        and position.get("exit_trigger_bar_close_time")
    ):
        try:
            return (
                format_utc_timestamp(
                    parse_aware_utc(
                        str(position["exit_trigger_bar_close_time"]),
                        "exit_trigger_bar_close_time",
                    )
                ),
                "exit_trigger_bar_close_time_v1",
            )
        except ValueError:
            return None, None

    if position.get("status") not in {
        "TAKE_PROFIT_HIT",
        "TIMEOUT_EXIT",
        "STOP_LOSS_HIT",
    }:
        return None, None
    opened_epoch = _epoch_seconds(position.get("last_checked_bar_time"))
    interval_seconds = _FIXED_INTERVAL_SECONDS.get(
        str(position.get("timeframe") or "").lower()
    )
    if opened_epoch is None or interval_seconds is None:
        return None, None
    try:
        bar_open = datetime.fromtimestamp(opened_epoch, timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None, None
    close_time = (
        bar_open + timedelta(seconds=interval_seconds) - timedelta(milliseconds=1)
    )
    return (
        format_utc_timestamp(close_time),
        "last_checked_bar_time_plus_timeframe_binance_v1",
    )


class _StaticFundingAdapter:
    def __init__(self, events: list[dict[str, Any]]):
        self.events = list(events)

    def get_funding_events(
        self, symbol: str, lookback_seconds: int
    ) -> list[dict[str, Any]]:
        del symbol, lookback_seconds
        return list(self.events)


def _reason_for_partial(
    events: list[dict[str, Any]],
    position: dict[str, Any],
    close_boundary: str,
) -> str:
    if not events:
        return "NO_EVENTS"
    try:
        opened = parse_aware_utc(
            str(position.get("opened_at") or ""), "opened_at"
        )
        closed = parse_aware_utc(close_boundary, "close_boundary")
    except ValueError:
        return "CLOSE_BOUNDARY_UNRESOLVED"

    parsed: list[tuple[datetime, int]] = []
    for event in events:
        raw_time = event.get("funding_event_at") or event.get("exchange_event_at")
        try:
            at = parse_aware_utc(str(raw_time or ""), "funding_event")
            interval = int(event.get("funding_interval_seconds") or 0)
        except (TypeError, ValueError):
            continue
        parsed.append((at, interval))
    if not parsed:
        return "MALFORMED_EVENTS"
    parsed.sort(key=lambda item: item[0])
    times = [item[0] for item in parsed]
    if not any(at <= opened for at in times):
        return "NO_BEFORE_BRACKET"
    if not any(at >= closed for at in times):
        return "NO_AFTER_BRACKET"
    intervals = [interval for _at, interval in parsed if interval > 0]
    if not intervals:
        return "INTERVAL_UNKNOWN"
    interval = min(intervals)
    bracket_start = max(at for at in times if at <= opened)
    bracket_end = min(at for at in times if at >= closed)
    span = [at for at in times if bracket_start <= at <= bracket_end]
    if any(
        (later - earlier).total_seconds() > interval
        for earlier, later in zip(span, span[1:])
    ):
        return "WINDOW_GAP"
    return "ENRICHMENT_PARTIAL"


def _increment_reason(stats: dict[str, Any], reason: str) -> None:
    breakdown = stats["funding_replay_reason_breakdown"]
    breakdown[reason] = breakdown.get(reason, 0) + 1


def re_enrich_closed_positions_funding(
    positions: list[dict[str, Any]],
    adapter: Any,
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Replay explicitly prospective incomplete terminal funding evidence.

    Only records carrying ``funding_events_verified_complete=False`` are eligible.
    Legacy positions that predate the prospective enrichment field are deliberately
    skipped: replay must not backfill historical positions into P1-03 evidence.

    One public funding query is made per symbol. Candidates are never reopened,
    and unresolved/old/source-failed records remain PARTIAL without ledger churn.
    """
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stats: dict[str, Any] = {
        "funding_replay_candidates": 0,
        "funding_replay_completed": 0,
        "funding_replay_still_partial": 0,
        "funding_replay_skipped_already_complete": 0,
        "funding_replay_skipped_not_prospective": 0,
        "funding_replay_errors": 0,
        "funding_replay_unresolved_close_boundary": 0,
        "funding_replay_reason_breakdown": {},
    }
    prepared: dict[str, list[tuple[dict[str, Any], str, int]]] = defaultdict(list)

    for position in positions:
        if position.get("status") not in CLOSED_STATUSES:
            continue
        funding_complete = position.get("funding_events_verified_complete")
        if funding_complete is True:
            stats["funding_replay_skipped_already_complete"] += 1
            continue
        if funding_complete is not False:
            stats["funding_replay_skipped_not_prospective"] += 1
            continue
        stats["funding_replay_candidates"] += 1

        close_boundary, _source = resolve_position_funding_close_boundary(position)
        if close_boundary is None:
            stats["funding_replay_still_partial"] += 1
            stats["funding_replay_unresolved_close_boundary"] += 1
            _increment_reason(stats, "CLOSE_BOUNDARY_UNRESOLVED")
            continue
        try:
            opened = parse_aware_utc(
                str(position.get("opened_at") or ""), "opened_at"
            )
            closed = parse_aware_utc(close_boundary, "close_boundary")
        except ValueError:
            stats["funding_replay_still_partial"] += 1
            stats["funding_replay_unresolved_close_boundary"] += 1
            _increment_reason(stats, "CLOSE_BOUNDARY_UNRESOLVED")
            continue
        if closed < opened or opened > now_utc or closed > now_utc:
            stats["funding_replay_still_partial"] += 1
            stats["funding_replay_unresolved_close_boundary"] += 1
            _increment_reason(stats, "CLOSE_BOUNDARY_UNRESOLVED")
            continue

        required = max(
            1,
            math.ceil((now_utc - opened).total_seconds())
            + FUNDING_LOOKBACK_CUSHION_SECONDS,
        )
        if required > MAX_FUNDING_REPLAY_LOOKBACK_SECONDS:
            stats["funding_replay_still_partial"] += 1
            _increment_reason(stats, "LOOKBACK_TOO_OLD")
            continue
        symbol = str(position.get("symbol") or "").upper()
        if not symbol:
            stats["funding_replay_still_partial"] += 1
            _increment_reason(stats, "INVALID_SYMBOL")
            continue
        prepared[symbol].append((position, close_boundary, required))

    updates: list[dict[str, Any]] = []
    for symbol, candidates in prepared.items():
        max_lookback = max(item[2] for item in candidates)
        try:
            raw = adapter.get_funding_events(symbol, max_lookback)
            if not isinstance(raw, list):
                raise ValueError("funding events are not a list")
        except Exception:
            for _position, _boundary, _required in candidates:
                stats["funding_replay_still_partial"] += 1
                stats["funding_replay_errors"] += 1
                _increment_reason(stats, "SOURCE_FAILURE")
            continue

        static_adapter = _StaticFundingAdapter(raw)
        for position, close_boundary, required in candidates:
            close_source = resolve_position_funding_close_boundary(position)[1]
            candidate = dict(position)
            try:
                enriched = enrich_closed_position_funding(
                    candidate,
                    static_adapter,
                    lookback_seconds=required,
                    bar_close_time=close_boundary,
                )
            except Exception:
                stats["funding_replay_still_partial"] += 1
                stats["funding_replay_errors"] += 1
                _increment_reason(stats, "ENRICHMENT_ERROR")
                continue
            if enriched.get("funding_events_verified_complete") is True:
                enriched["funding_attribution_close_time"] = close_boundary
                enriched["funding_attribution_close_source"] = close_source
                enriched["funding_replay_version"] = FUNDING_REPLAY_VERSION
                updates.append(enriched)
                stats["funding_replay_completed"] += 1
            else:
                stats["funding_replay_still_partial"] += 1
                _increment_reason(
                    stats, _reason_for_partial(raw, position, close_boundary)
                )

    return updates, stats


def funding_replay_record_fingerprint(record: dict[str, Any]) -> str:
    """Evidence-aware fingerprint for one monotonic replay ledger record."""
    events = (
        record.get("funding_events")
        if isinstance(record.get("funding_events"), list)
        else []
    )
    payload = {
        "version": FUNDING_REPLAY_VERSION,
        "position_state": position_state_fingerprint(record),
        "verified_complete": record.get("funding_events_verified_complete") is True,
        "funding_events": events,
        "close_time": record.get("funding_attribution_close_time"),
        "close_source": record.get("funding_attribution_close_source"),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(encoded.encode()).hexdigest()[:16]
