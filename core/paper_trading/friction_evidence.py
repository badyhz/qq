"""Append-only public friction evidence for Shadow research.

This module has no authenticated API, account, order, fill, Testnet or Live
capability. Book-derived impact is explicitly an estimate, never actual
slippage. Runtime evidence is stored in one stable JSONL artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, getcontext
from typing import Any, Iterable

import yaml

from core.paper_trading.strategy_config import load_strategy_config


getcontext().prec = 34
EVIDENCE_VERSION = "friction_evidence_v1"
ATTRIBUTION_VERSION = "position_funding_events_v1"
STORE_FILENAME = "friction_evidence.jsonl"
QUALITY_STATUSES = {
    "VALID", "STALE", "CROSSED_BOOK", "INVALID_PRICE", "MISSING_TIMESTAMP",
    "SOURCE_ERROR", "INSUFFICIENT_DEPTH", "PARTIAL", "UNAVAILABLE",
}
REQUIRED_FIELDS = {
    "evidence_version", "evidence_type", "evidence_id", "venue", "market_type",
    "symbol", "source", "source_endpoint_or_adapter", "observed_at",
    "exchange_event_at", "collected_at", "pipeline_run_id", "pipeline_commit",
    "report_date", "payload_hash", "quality_status",
}
_NON_SEMANTIC_HASH_FIELDS = {
    "evidence_id", "payload_hash", "collected_at", "pipeline_run_id",
    "pipeline_commit", "report_date",
}
_BPS = Decimal("10000")
_ZERO = Decimal("0")


def _decimal(value: Any, field: str, *, positive: bool = False, nonnegative: bool = False) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    if positive and result <= 0:
        raise ValueError(f"{field} must be positive")
    if nonnegative and result < 0:
        raise ValueError(f"{field} must be nonnegative")
    return result


def _text(value: Decimal) -> str:
    return "0" if value == 0 else format(value.normalize(), "f")


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware timestamp")
    return parsed.astimezone(timezone.utc)


def _utc_text(value: Any, field: str) -> str:
    return _utc(value, field).isoformat(timespec="milliseconds")


def _canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, Decimal):
        return _text(value)
    if isinstance(value, float):
        return _text(_decimal(value, "value"))
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise ValueError(f"unsupported payload type: {type(value).__name__}")


def _hash(value: Any) -> str:
    encoded = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def payload_hash(record: dict[str, Any]) -> str:
    semantic = {key: value for key, value in record.items() if key not in _NON_SEMANTIC_HASH_FIELDS}
    return _hash(semantic)


def evidence_id(record: dict[str, Any]) -> str:
    kind = record.get("evidence_type")
    if kind in {"TOP_OF_BOOK", "DEPTH_BOOK_IMPACT_ESTIMATE", "FUNDING_QUERY_COVERAGE"}:
        identity = [record.get(key) for key in (
            "venue", "market_type", "symbol", "exchange_event_at", "evidence_type",
        )]
    elif kind == "FUNDING_EVENT":
        identity = [record.get(key) for key in ("venue", "symbol", "exchange_event_at", "evidence_type")]
    elif kind == "POSITION_FUNDING_ATTRIBUTION":
        identity = [record.get("position_id"), sorted(record.get("funding_evidence_ids", [])), ATTRIBUTION_VERSION]
    else:
        identity = [record.get(key) for key in (
            "venue", "market_type", "symbol", "exchange_event_at", "evidence_type",
            "pipeline_run_id",
        )]
    return hashlib.sha256("|".join(str(item) for item in identity).encode()).hexdigest()


def _validate_report_date(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("report_date must be YYYY-MM-DD")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError("report_date must be YYYY-MM-DD") from exc
    return value


def finalize_record(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["evidence_version"] = EVIDENCE_VERSION
    for field in ("observed_at", "exchange_event_at", "collected_at"):
        result[field] = _utc_text(result.get(field), field)
    result["report_date"] = _validate_report_date(result.get("report_date"))
    for field in ("evidence_type", "venue", "market_type", "symbol", "source",
                  "source_endpoint_or_adapter", "pipeline_run_id", "pipeline_commit"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if result.get("quality_status") not in QUALITY_STATUSES:
        raise ValueError("unsupported quality_status")
    result["evidence_id"] = evidence_id(result)
    result["payload_hash"] = payload_hash(result)
    missing = REQUIRED_FIELDS - result.keys()
    if missing:
        raise ValueError(f"missing evidence fields: {sorted(missing)}")
    return _canonical(result)


@dataclass(frozen=True)
class AppendResult:
    status: str
    evidence_id: str
    path: str


class EvidenceStore:
    """Single-file append-only JSONL store with deterministic dedup/conflicts."""

    def __init__(self, path: str):
        self.path = path

    def read_all(self) -> list[dict[str, Any]]:
        if not os.path.isfile(self.path):
            return []
        records: list[dict[str, Any]] = []
        with open(self.path, encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"malformed evidence JSONL line {line_number}") from exc
                if not isinstance(record, dict) or REQUIRED_FIELDS - record.keys():
                    raise ValueError(f"malformed evidence record line {line_number}")
                records.append(record)
        return records

    def append(self, raw_record: dict[str, Any]) -> AppendResult:
        record = finalize_record(raw_record)
        existing = {item["evidence_id"]: item for item in self.read_all()}
        prior = existing.get(record["evidence_id"])
        if prior is not None:
            if prior.get("payload_hash") == record["payload_hash"]:
                return AppendResult("EXACT_DUPLICATE_NO_WRITE", record["evidence_id"], self.path)
            return AppendResult("CONFLICT_REJECTED", record["evidence_id"], self.path)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return AppendResult("APPENDED", record["evidence_id"], self.path)


def load_evidence_config(strategy_config_path: str) -> dict[str, Any]:
    with open(strategy_config_path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    config = raw.get("friction_evidence") if isinstance(raw, dict) else None
    if not isinstance(config, dict):
        raise ValueError("friction_evidence configuration is unavailable")
    required = {
        "enabled", "evidence_version", "venue", "market_type", "public_adapter",
        "depth_limit", "diagnostic_notional_bands", "staleness_threshold_seconds",
        "storage_filename", "funding_synchronization_lookback_seconds", "readiness_targets",
    }
    if required - config.keys():
        raise ValueError(f"missing friction evidence config: {sorted(required - config.keys())}")
    if config["evidence_version"] != EVIDENCE_VERSION:
        raise ValueError("unsupported evidence version")
    if config["venue"] != "binance" or config["market_type"] != "linear_perpetual":
        raise ValueError("unsupported venue or instrument")
    if config["public_adapter"] != "binance_usdm_public":
        raise ValueError("unsupported public adapter")
    if config["storage_filename"] != STORE_FILENAME:
        raise ValueError("evidence storage must use the stable JSONL filename")
    bands = [_decimal(item, "diagnostic_notional_band", positive=True) for item in config["diagnostic_notional_bands"]]
    if not bands or len(set(bands)) != len(bands):
        raise ValueError("diagnostic notional bands must be unique and non-empty")
    if int(config["depth_limit"]) <= 0 or int(config["staleness_threshold_seconds"]) <= 0:
        raise ValueError("depth limit and staleness threshold must be positive")
    forbidden = {"api_key", "secret", "assumptions_hash", "cohort_activation", "approved_fee_bps"}
    if any(key.lower() in forbidden for key in _walk_keys(config)):
        raise ValueError("evidence configuration contains forbidden activation or secret fields")
    return _canonical(config)


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def resolve_active_universe(strategy_config_path: str, config: dict[str, Any]) -> dict[str, Any]:
    library = load_strategy_config(strategy_config_path)
    symbols: set[str] = set()
    enabled_strategy_ids: list[str] = []
    for strategy_id, strategy in library.enabled_strategies.items():
        api = library.data_apis[strategy.data_api]
        if api.market != "usdm_futures" or not api.readonly or api.requires_secret or api.allows_orders:
            raise ValueError("enabled strategy uses unsupported venue or instrument")
        symbols.update(strategy.symbols)
        enabled_strategy_ids.append(strategy_id)
    if any(symbol != str(symbol).upper() or not str(symbol).endswith("USDT") for symbol in symbols):
        raise ValueError("active universe contains invalid symbol")
    with open(strategy_config_path, "rb") as handle:
        inventory_hash = hashlib.sha256(handle.read()).hexdigest()
    return {
        "venue": config["venue"],
        "market_type": config["market_type"],
        "symbols": sorted(symbols),
        "enabled_strategy_ids": sorted(enabled_strategy_ids),
        "strategy_inventory_hash": inventory_hash,
    }


def _base_record(
    *, kind: str, symbol: str, event_at: str, source: str, endpoint: str,
    context: dict[str, str], config: dict[str, Any], inventory_hash: str,
) -> dict[str, Any]:
    return {
        "evidence_version": EVIDENCE_VERSION,
        "evidence_type": kind,
        "venue": config["venue"],
        "market_type": config["market_type"],
        "symbol": symbol,
        "source": source,
        "source_endpoint_or_adapter": endpoint,
        "observed_at": event_at,
        "exchange_event_at": event_at,
        "collected_at": context["collected_at"],
        "pipeline_run_id": context["pipeline_run_id"],
        "pipeline_commit": context["pipeline_commit"],
        "report_date": context["report_date"],
        "strategy_inventory_hash": inventory_hash,
        "quality_status": "VALID",
    }


def build_top_of_book_evidence(
    raw: dict[str, Any], *, expected_symbol: str, context: dict[str, str],
    config: dict[str, Any], inventory_hash: str,
) -> dict[str, Any]:
    if raw.get("symbol") != expected_symbol:
        raise ValueError("top-of-book symbol mismatch")
    bid = _decimal(raw.get("best_bid_price"), "best_bid_price", positive=True)
    ask = _decimal(raw.get("best_ask_price"), "best_ask_price", positive=True)
    bid_qty = _decimal(raw.get("best_bid_quantity"), "best_bid_quantity", nonnegative=True)
    ask_qty = _decimal(raw.get("best_ask_quantity"), "best_ask_quantity", nonnegative=True)
    if ask < bid:
        raise ValueError("CROSSED_BOOK")
    event_at = _utc_text(raw.get("exchange_event_at"), "exchange_event_at")
    collected = _utc(context["collected_at"], "collected_at")
    observed = _utc(event_at, "exchange_event_at")
    mid = (bid + ask) / 2
    full = (ask - bid) / mid * _BPS
    result = _base_record(
        kind="TOP_OF_BOOK", symbol=expected_symbol, event_at=event_at,
        source=str(raw.get("source") or "binance_public"), endpoint="GET /fapi/v1/ticker/bookTicker",
        context=context, config=config, inventory_hash=inventory_hash,
    )
    result.update({
        "best_bid_price": _text(bid), "best_bid_quantity": _text(bid_qty),
        "best_ask_price": _text(ask), "best_ask_quantity": _text(ask_qty),
        "mid_price": _text(mid), "full_spread_bps": _text(full),
        "one_leg_adverse_spread_bps": _text(full / 2),
        "quality_status": (
            "STALE" if (collected - observed).total_seconds() > int(config["staleness_threshold_seconds"])
            else "VALID"
        ),
    })
    return finalize_record(result)


def _validated_levels(raw_levels: Any, side: str) -> list[tuple[Decimal, Decimal]]:
    if not isinstance(raw_levels, list) or not raw_levels:
        raise ValueError(f"{side} levels must be non-empty")
    levels: dict[Decimal, Decimal] = {}
    for raw in raw_levels:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            raise ValueError(f"malformed {side} level")
        price = _decimal(raw[0], f"{side} price", positive=True)
        quantity = _decimal(raw[1], f"{side} quantity", positive=True)
        levels[price] = levels.get(price, _ZERO) + quantity
    reverse = side == "bids"
    return sorted(levels.items(), key=lambda item: item[0], reverse=reverse)


def book_impact(levels: list[tuple[Decimal, Decimal]], target_quote: Decimal, reference: Decimal) -> dict[str, Any]:
    remaining = target_quote
    base_filled = _ZERO
    quote_filled = _ZERO
    consumed = 0
    for price, quantity in levels:
        available_quote = price * quantity
        take_quote = min(remaining, available_quote)
        if take_quote <= 0:
            break
        base_filled += take_quote / price
        quote_filled += take_quote
        remaining -= take_quote
        consumed += 1
        if remaining == 0:
            break
    complete = remaining == 0
    vwap = quote_filled / base_filled if base_filled else _ZERO
    displacement = abs(vwap - reference) / reference * _BPS if complete else _ZERO
    return {
        "target_notional": _text(target_quote),
        "filled_notional": _text(quote_filled),
        "fill_complete": complete,
        "levels_consumed": consumed,
        "vwap_price": _text(vwap),
        "reference_price": _text(reference),
        "adverse_impact_bps": _text(displacement),
        "impact_label": "BOOK_IMPACT_ESTIMATE",
    }


def build_depth_evidence(
    raw: dict[str, Any], *, expected_symbol: str, context: dict[str, str],
    config: dict[str, Any], inventory_hash: str,
) -> dict[str, Any]:
    if raw.get("symbol") != expected_symbol:
        raise ValueError("depth symbol mismatch")
    bids = _validated_levels(raw.get("bids"), "bids")
    asks = _validated_levels(raw.get("asks"), "asks")
    if asks[0][0] < bids[0][0]:
        raise ValueError("CROSSED_BOOK")
    event_at = _utc_text(raw.get("exchange_event_at"), "exchange_event_at")
    bands = [_decimal(item, "diagnostic_notional_band", positive=True) for item in config["diagnostic_notional_bands"]]
    buy = {str(_text(band)): book_impact(asks, band, asks[0][0]) for band in bands}
    sell = {str(_text(band)): book_impact(bids, band, bids[0][0]) for band in bands}
    complete = all(item["fill_complete"] for item in (*buy.values(), *sell.values()))
    result = _base_record(
        kind="DEPTH_BOOK_IMPACT_ESTIMATE", symbol=expected_symbol, event_at=event_at,
        source=str(raw.get("source") or "binance_public"), endpoint="GET /fapi/v1/depth",
        context=context, config=config, inventory_hash=inventory_hash,
    )
    result.update({
        "depth_limit": int(config["depth_limit"]),
        "bid_levels": [[_text(p), _text(q)] for p, q in bids[:int(config["depth_limit"])]],
        "ask_levels": [[_text(p), _text(q)] for p, q in asks[:int(config["depth_limit"])]],
        "diagnostic_notional_bands": [_text(item) for item in bands],
        "buy_book_impact_bps_by_notional": buy,
        "sell_book_impact_bps_by_notional": sell,
        "quality_status": "VALID" if complete else "INSUFFICIENT_DEPTH",
        "actual_slippage_available": False,
    })
    return finalize_record(result)


def build_funding_evidence(
    raw: dict[str, Any], *, expected_symbol: str, context: dict[str, str],
    config: dict[str, Any], inventory_hash: str,
) -> dict[str, Any]:
    if raw.get("symbol") != expected_symbol:
        raise ValueError("funding symbol mismatch")
    rate = _decimal(raw.get("signed_funding_rate"), "signed_funding_rate")
    mark = _decimal(raw.get("mark_price"), "mark_price", positive=True)
    event_at = _utc_text(raw.get("funding_event_at"), "funding_event_at")
    interval = int(raw.get("funding_interval_seconds") or 0)
    if interval <= 0:
        raise ValueError("funding interval must be known and positive")
    result = _base_record(
        kind="FUNDING_EVENT", symbol=expected_symbol, event_at=event_at,
        source=str(raw.get("source") or "binance_public"), endpoint="GET /fapi/v1/fundingRate",
        context=context, config=config, inventory_hash=inventory_hash,
    )
    result.update({
        "signed_funding_rate": _text(rate),
        "mark_price": _text(mark),
        "funding_interval_seconds": interval,
        "source_event_identity": str(raw.get("source_event_identity") or f"{expected_symbol}:{event_at}"),
    })
    return finalize_record(result)


def build_quality_failure_evidence(
    *, symbol: str, failed_evidence_type: str, context: dict[str, str],
    config: dict[str, Any], inventory_hash: str, error_class: str,
) -> dict[str, Any]:
    """Persist a non-price failure fact without fabricating market values."""
    result = _base_record(
        kind="SOURCE_QUALITY_FAILURE", symbol=symbol, event_at=context["collected_at"],
        source="collector_validation", endpoint=config["public_adapter"], context=context,
        config=config, inventory_hash=inventory_hash,
    )
    result.update({
        "failed_evidence_type": failed_evidence_type,
        "error_class": error_class,
        "quality_status": "SOURCE_ERROR",
    })
    return finalize_record(result)


def build_funding_coverage_evidence(
    *, symbol: str, events: list[dict[str, Any]], context: dict[str, str],
    config: dict[str, Any], inventory_hash: str,
) -> dict[str, Any]:
    """Record query success separately from event rows; zero is not complete."""
    event_times = sorted(_utc(item["funding_event_at"], "funding_event_at") for item in events)
    intervals = [int(item.get("funding_interval_seconds") or 0) for item in events]
    known_intervals = [item for item in intervals if item > 0]
    interval = min(known_intervals) if known_intervals else 0
    query_end = _utc(context["collected_at"], "collected_at")
    query_start = query_end - timedelta(seconds=int(config["funding_synchronization_lookback_seconds"]))
    continuity = bool(
        events and interval
        and (event_times[0] - query_start).total_seconds() <= interval
        and (query_end - event_times[-1]).total_seconds() <= interval
        and all(
            int((later - earlier).total_seconds()) <= interval
            for earlier, later in zip(event_times, event_times[1:])
        )
    )
    result = _base_record(
        kind="FUNDING_QUERY_COVERAGE", symbol=symbol, event_at=context["collected_at"],
        source="binance_usdm_public", endpoint="GET /fapi/v1/fundingRate",
        context=context, config=config, inventory_hash=inventory_hash,
    )
    result.update({
        "query_succeeded": True,
        "query_started_at": query_start.isoformat(timespec="milliseconds"),
        "query_ended_at": query_end.isoformat(timespec="milliseconds"),
        "returned_event_count": len(events),
        "funding_interval_seconds": interval or None,
        "expected_windows_resolved": continuity,
        "zero_events_proven": False,
        "quality_status": "VALID" if continuity else "PARTIAL",
    })
    return finalize_record(result)


def attribute_position_funding(
    position: dict[str, Any], funding_records: Iterable[dict[str, Any]], *,
    query_succeeded: bool, expected_windows_resolved: bool,
) -> dict[str, Any]:
    opened = _utc(position.get("opened_at"), "opened_at")
    closed = _utc(position.get("closed_at"), "closed_at")
    if closed < opened:
        raise ValueError("closed_at precedes opened_at")
    side = str(position.get("side") or "").upper()
    if side not in {"LONG", "SHORT"}:
        raise ValueError("position direction must be LONG or SHORT")
    symbol = str(position.get("symbol") or "")
    quantity = _decimal(position.get("position_size_preview"), "position_size_preview", positive=True)
    risk = abs(
        _decimal(position.get("entry_price"), "entry_price", positive=True)
        - _decimal(position.get("stop_loss"), "stop_loss", positive=True)
    ) * quantity
    if risk <= 0:
        raise ValueError("risk denominator must be positive")
    selected: list[dict[str, Any]] = []
    effect = _ZERO
    for record in funding_records:
        if record.get("evidence_type") != "FUNDING_EVENT" or record.get("symbol") != symbol:
            continue
        at = _utc(record.get("exchange_event_at"), "funding event")
        if not (opened < at <= closed):
            continue
        rate = _decimal(record.get("signed_funding_rate"), "signed_funding_rate")
        mark = _decimal(record.get("mark_price", position.get("entry_price")), "mark_price", positive=True)
        effect += -(mark * quantity * rate) if side == "LONG" else mark * quantity * rate
        selected.append(record)
    complete = query_succeeded and expected_windows_resolved
    return {
        "position_id": position.get("position_id"),
        "symbol": symbol,
        "direction": side,
        "funding_evidence_ids": sorted(record["evidence_id"] for record in selected),
        "event_count": len(selected),
        "signed_rates": [record["signed_funding_rate"] for record in selected],
        "funding_effect_quote": _text(effect),
        "funding_effect_r": _text(effect / risk),
        "attribution_version": ATTRIBUTION_VERSION,
        "funding_completeness": "COMPLETE" if complete else "PARTIAL",
        "zero_events_proven": bool(complete and not selected),
    }


def build_position_funding_attribution_evidence(
    position: dict[str, Any], funding_records: Iterable[dict[str, Any]], *,
    query_succeeded: bool, expected_windows_resolved: bool,
    context: dict[str, str], config: dict[str, Any], inventory_hash: str,
) -> dict[str, Any]:
    attribution = attribute_position_funding(
        position, funding_records, query_succeeded=query_succeeded,
        expected_windows_resolved=expected_windows_resolved,
    )
    result = _base_record(
        kind="POSITION_FUNDING_ATTRIBUTION", symbol=attribution["symbol"],
        event_at=_utc_text(position.get("closed_at"), "closed_at"),
        source="derived_from_public_funding_evidence",
        endpoint="position_funding_events_v1", context=context,
        config=config, inventory_hash=inventory_hash,
    )
    result.update(attribution)
    result["quality_status"] = (
        "VALID" if attribution["funding_completeness"] == "COMPLETE" else "PARTIAL"
    )
    return finalize_record(result)


def stop_evidence_summary(positions: Iterable[dict[str, Any]], prospective_start_at: str) -> dict[str, Any]:
    boundary = _utc(prospective_start_at, "prospective_start_at")
    stops = [
        position for position in positions
        if position.get("status") == "STOP_LOSS_HIT"
        and _utc(position.get("closed_at"), "closed_at") >= boundary
    ]
    valid = [position for position in stops if (
        position.get("gap_execution_evidence_version") == "stop_trigger_bar_open_v1"
        and position.get("exit_trigger_bar_open") is not None
        and position.get("exit_trigger_bar_close_time") is not None
        and position.get("gap_execution_reference_price") is not None
    )]
    normal = sum(
        _decimal(position["gap_execution_reference_price"], "gap")
        == _decimal(position.get("nominal_stop_price"), "stop") for position in valid
    )
    return {
        "prospective_stop_count": len(stops),
        "prospective_stop_with_gap_evidence": len(valid),
        "prospective_stop_missing_gap_evidence": len(stops) - len(valid),
        "prospective_gap_coverage_ratio": _text(Decimal(len(valid)) / len(stops)) if stops else "0",
        "long_stop_count": sum(str(position.get("side")).upper() == "LONG" for position in stops),
        "short_stop_count": sum(str(position.get("side")).upper() == "SHORT" for position in stops),
        "normal_stop_count": normal,
        "gap_through_stop_count": len(valid) - normal,
        "strategy_ids": sorted({str(position.get("strategy_id") or "") for position in stops if position.get("strategy_id")}),
    }


def _percentile(values: list[Decimal], percentile: Decimal) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = int((Decimal(len(ordered) - 1) * percentile).to_integral_value(rounding="ROUND_HALF_UP"))
    return _text(ordered[rank])


def build_readiness_report(
    records: Iterable[dict[str, Any]], *, universe: dict[str, Any],
    positions: Iterable[dict[str, Any]], prospective_start_at: str,
    config: dict[str, Any], funding_continuity: dict[str, bool] | None = None,
    funding_conflicts: dict[str, int] | None = None,
) -> dict[str, Any]:
    rows = list(records)
    targets = config["readiness_targets"]
    per_symbol: dict[str, Any] = {}
    all_targets = True
    observation_dates: set[str] = set()
    funding_continuity = funding_continuity or {}
    funding_conflicts = funding_conflicts or {}
    for symbol in universe["symbols"]:
        books = [row for row in rows if row.get("symbol") == symbol and row.get("evidence_type") == "TOP_OF_BOOK"]
        depths = [row for row in rows if row.get("symbol") == symbol and row.get("evidence_type") == "DEPTH_BOOK_IMPACT_ESTIMATE"]
        funding = [row for row in rows if row.get("symbol") == symbol and row.get("evidence_type") == "FUNDING_EVENT"]
        coverage_rows = [row for row in rows if row.get("symbol") == symbol and row.get("evidence_type") == "FUNDING_QUERY_COVERAGE"]
        continuity_resolved = bool(funding_continuity.get(symbol)) or any(
            row.get("expected_windows_resolved") is True for row in coverage_rows
        )
        valid_books = [row for row in books if row.get("quality_status") == "VALID"]
        valid_depths = [row for row in depths if row.get("quality_status") == "VALID"]
        observation_dates.update(str(row.get("observed_at", ""))[:10] for row in valid_books)
        spreads = [_decimal(row["one_leg_adverse_spread_bps"], "spread") for row in valid_books]
        def impacts(side: str, band: str) -> list[Decimal]:
            field = f"{side}_book_impact_bps_by_notional"
            return [
                _decimal(row[field][band]["adverse_impact_bps"], "impact")
                for row in valid_depths if band in row.get(field, {})
            ]
        bands = [str(item) for item in config["diagnostic_notional_bands"]]
        success = Decimal(len(valid_books)) / len(books) if books else _ZERO
        symbol_ready = (
            len(valid_books) >= int(targets["minimum_snapshots_per_symbol"])
            and success >= _decimal(targets["minimum_success_ratio"], "minimum_success_ratio")
            and continuity_resolved
        )
        all_targets = all_targets and symbol_ready
        per_symbol[symbol] = {
            "first_observation_at": min((row["observed_at"] for row in books), default=None),
            "last_observation_at": max((row["observed_at"] for row in books), default=None),
            "valid_book_snapshot_count": len(valid_books),
            "invalid_book_snapshot_count": len(books) - len(valid_books),
            "snapshot_success_ratio": _text(success),
            "valid_depth_snapshot_count": len(valid_depths),
            "insufficient_depth_count": sum(row.get("quality_status") == "INSUFFICIENT_DEPTH" for row in depths),
            "median_one_leg_spread_bps": _percentile(spreads, Decimal("0.5")),
            "p75_one_leg_spread_bps": _percentile(spreads, Decimal("0.75")),
            "p90_one_leg_spread_bps": _percentile(spreads, Decimal("0.90")),
            "p95_one_leg_spread_bps": _percentile(spreads, Decimal("0.95")),
            "median_buy_impact_bps_by_notional": {band: _percentile(impacts("buy", band), Decimal("0.5")) for band in bands},
            "p90_buy_impact_bps_by_notional": {band: _percentile(impacts("buy", band), Decimal("0.9")) for band in bands},
            "median_sell_impact_bps_by_notional": {band: _percentile(impacts("sell", band), Decimal("0.5")) for band in bands},
            "p90_sell_impact_bps_by_notional": {band: _percentile(impacts("sell", band), Decimal("0.9")) for band in bands},
            "funding_event_count": len(funding),
            "funding_first_at": min((row["exchange_event_at"] for row in funding), default=None),
            "funding_last_at": max((row["exchange_event_at"] for row in funding), default=None),
            "funding_conflict_count": int(funding_conflicts.get(symbol, 0)),
            "funding_continuity_resolved": continuity_resolved,
            "symbol_readiness": "READY" if symbol_ready else "MORE_DATA",
        }
    stop_summary = stop_evidence_summary(positions, prospective_start_at)
    days = len(observation_dates)
    stop_ready = (
        stop_summary["prospective_stop_count"] >= int(targets["minimum_prospective_stops"])
        and stop_summary["prospective_gap_coverage_ratio"] == "1"
        and stop_summary["long_stop_count"] > 0
        and stop_summary["short_stop_count"] > 0
        and set(universe["enabled_strategy_ids"]).issubset(stop_summary["strategy_ids"])
    )
    all_targets = all_targets and stop_ready and days >= int(targets["minimum_calendar_days"])
    return {
        "evidence_version": EVIDENCE_VERSION,
        "status": "READY_FOR_HUMAN_REVIEW" if all_targets else "MORE_DATA",
        "observation_calendar_days": days,
        "per_symbol": per_symbol,
        "prospective_stops": stop_summary,
        "targets": targets,
        "actual_account_fee_tier": "UNVERIFIED",
        "assumptions_approved": False,
        "p1_03_cohort_activated": False,
        "testnet_enabled": False,
        "live_enabled": False,
        "human_approval_required": True,
    }


def write_readiness_report(report: dict[str, Any], path: str) -> str:
    """Atomically replace the derived summary; evidence JSONL stays append-only."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".friction-readiness-", suffix=".json", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(_canonical(report), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def collect_evidence_cycle(
    *, strategy_config_path: str, output_dir: str, adapter: Any,
    context: dict[str, str], observation_only: bool = True,
) -> dict[str, Any]:
    config = load_evidence_config(strategy_config_path)
    if not config["enabled"] and not context.get("fixture_mode"):
        return {"status": "DISABLED", "appended": 0, "duplicates": 0, "conflicts": 0}
    universe = resolve_active_universe(strategy_config_path, config)
    store = EvidenceStore(os.path.join(output_dir, config["storage_filename"]))
    counts = {"appended": 0, "duplicates": 0, "conflicts": 0, "source_errors": 0}
    requested: set[str] = set()
    for symbol in universe["symbols"]:
        requested.add(symbol)
        builders = (
            ("TOP_OF_BOOK", adapter.get_top_of_book, build_top_of_book_evidence),
            ("DEPTH_BOOK_IMPACT_ESTIMATE", lambda item: adapter.get_depth(item, int(config["depth_limit"])), build_depth_evidence),
        )
        for evidence_type, fetch, builder in builders:
            try:
                record = builder(
                    fetch(symbol), expected_symbol=symbol, context=context,
                    config=config, inventory_hash=universe["strategy_inventory_hash"],
                )
                outcome = store.append(record)
                counts["appended" if outcome.status == "APPENDED" else
                       "duplicates" if outcome.status == "EXACT_DUPLICATE_NO_WRITE" else "conflicts"] += 1
            except (OSError, ValueError, TypeError) as exc:
                counts["source_errors"] += 1
                failure = build_quality_failure_evidence(
                    symbol=symbol, failed_evidence_type=evidence_type, context=context,
                    config=config, inventory_hash=universe["strategy_inventory_hash"],
                    error_class=type(exc).__name__,
                )
                outcome = store.append(failure)
                counts["appended" if outcome.status == "APPENDED" else
                       "duplicates" if outcome.status == "EXACT_DUPLICATE_NO_WRITE" else "conflicts"] += 1
                if not observation_only:
                    raise
        try:
            events = adapter.get_funding_events(symbol, int(config["funding_synchronization_lookback_seconds"]))
            if not isinstance(events, list):
                raise ValueError("funding response must be a list")
            for event in events:
                record = build_funding_evidence(
                    event, expected_symbol=symbol, context=context, config=config,
                    inventory_hash=universe["strategy_inventory_hash"],
                )
                outcome = store.append(record)
                counts["appended" if outcome.status == "APPENDED" else
                       "duplicates" if outcome.status == "EXACT_DUPLICATE_NO_WRITE" else "conflicts"] += 1
            coverage = build_funding_coverage_evidence(
                symbol=symbol, events=events, context=context, config=config,
                inventory_hash=universe["strategy_inventory_hash"],
            )
            outcome = store.append(coverage)
            counts["appended" if outcome.status == "APPENDED" else
                   "duplicates" if outcome.status == "EXACT_DUPLICATE_NO_WRITE" else "conflicts"] += 1
        except (OSError, ValueError, TypeError) as exc:
            counts["source_errors"] += 1
            failure = build_quality_failure_evidence(
                symbol=symbol, failed_evidence_type="FUNDING_EVENT", context=context,
                config=config, inventory_hash=universe["strategy_inventory_hash"],
                error_class=type(exc).__name__,
            )
            outcome = store.append(failure)
            counts["appended" if outcome.status == "APPENDED" else
                   "duplicates" if outcome.status == "EXACT_DUPLICATE_NO_WRITE" else "conflicts"] += 1
            if not observation_only:
                raise
    counts.update({
        "status": "CONFLICT" if counts["conflicts"] else "PASS_WITH_SOURCE_ERRORS" if counts["source_errors"] else "PASS",
        "active_symbols": universe["symbols"],
        "active_symbol_count": len(universe["symbols"]),
        "duplicate_symbol_requests": len(requested) - len(universe["symbols"]),
        "store_path": store.path,
        "authenticated_calls": 0,
        "orders": 0,
    })
    return counts


def main(argv: list[str] | None = None) -> int:
    """Explicit public-read-only collection entry point for the existing cycle."""
    import argparse
    from core.paper_trading.data_source import DataSourceConfig
    from core.paper_trading.public_market_adapter import BinancePublicKlineAdapter

    parser = argparse.ArgumentParser(description="Collect public friction evidence (no orders)")
    parser.add_argument("--strategy-config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pipeline-run-id", required=True)
    parser.add_argument("--pipeline-commit", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--collected-at", required=True)
    parser.add_argument("--allow-public-http", action="store_true", default=False)
    args = parser.parse_args(argv)
    if not args.allow_public_http:
        parser.error("collector requires explicit --allow-public-http")
    config = load_evidence_config(args.strategy_config)
    if not config["enabled"]:
        print(json.dumps({"status": "DISABLED", "p1_03_cohort_activated": False}))
        return 0
    adapter = BinancePublicKlineAdapter(
        DataSourceConfig(mode="snapshot", network_enabled=True),
    )
    result = collect_evidence_cycle(
        strategy_config_path=args.strategy_config,
        output_dir=args.output_dir,
        adapter=adapter,
        context={
            "pipeline_run_id": args.pipeline_run_id,
            "pipeline_commit": args.pipeline_commit,
            "report_date": args.report_date,
            "collected_at": args.collected_at,
        },
        observation_only=True,
    )
    store = EvidenceStore(os.path.join(args.output_dir, config["storage_filename"]))
    records = store.read_all()
    if records:
        from core.paper_trading.paper_position import load_canonical_positions
        universe = resolve_active_universe(args.strategy_config, config)
        positions, _ = load_canonical_positions(args.output_dir)
        prospective_start = min(record["observed_at"] for record in records)
        report = build_readiness_report(
            records, universe=universe, positions=positions,
            prospective_start_at=prospective_start, config=config,
        )
        result["readiness_report_path"] = write_readiness_report(
            report, os.path.join(args.output_dir, "friction_evidence_readiness.json"),
        )
    print(json.dumps(result, sort_keys=True))
    return 1 if result["status"] == "CONFLICT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
