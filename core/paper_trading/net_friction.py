"""Versioned, derived execution-friction accounting for Shadow positions.

The canonical position ledger and its gross lifecycle values are immutable.
This module consumes a closed canonical position plus explicit assumptions and
returns a deterministic assessment.  It has no network, order, account or
credential capability.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, getcontext
from statistics import median
from typing import Any, Iterable


getcontext().prec = 34

FRICTION_MODEL_VERSION = "net_friction_v1"
COMPLETE_STATUSES = {"COMPLETE_OBSERVED", "COMPLETE_ESTIMATED"}
FRICTION_MODEL_STATUSES = (
    "COMPLETE_OBSERVED",
    "COMPLETE_ESTIMATED",
    "PARTIAL",
    "UNAVAILABLE",
    "INVALID",
    "NOT_APPLICABLE",
)
NET_FRICTION_ACTIVATION_FIELDS = (
    "net_friction_trusted_cohort_start_at",
    "net_friction_trusted_cohort_rule_version",
    "net_friction_trusted_cohort_start_run_id",
    "net_friction_trusted_cohort_start_commit",
    "net_friction_model_version",
    "net_friction_assumptions_hash",
)
SUPPORTED_INSTRUMENT_TYPES = {"linear_spot", "linear_perpetual"}
_CLOSED = {"TAKE_PROFIT_HIT", "STOP_LOSS_HIT", "TIMEOUT_EXIT"}
_BPS = Decimal("10000")
_ZERO = Decimal("0")


@dataclass(frozen=True)
class NetFrictionActivationResult:
    status: str
    manifest_path: str
    metadata: dict[str, str]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "manifest_path": self.manifest_path,
            "metadata": self.metadata,
            "error": self.error,
        }


def _decimal(value: Any, field: str, *, nonnegative: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be a decimal number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be a decimal number") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    if nonnegative and result < 0:
        raise ValueError(f"{field} must be nonnegative")
    return result


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


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _canonical(value: Any) -> Any:
    """Canonical JSON-compatible representation without binary-float drift."""
    if isinstance(value, dict):
        return {str(k): _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, float):
        return _decimal_text(_decimal(value, "configuration value"))
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise ValueError(f"unsupported configuration value type: {type(value).__name__}")


def assumptions_hash(assumptions: dict[str, Any]) -> str:
    payload = json.dumps(_canonical(assumptions), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def load_assumptions(path: str) -> dict[str, Any]:
    with open(path) as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("friction assumptions must be a JSON object")
    return value


def validate_assumptions(assumptions: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if assumptions.get("friction_model_version") != FRICTION_MODEL_VERSION:
        errors.append(f"friction_model_version must be {FRICTION_MODEL_VERSION}")
    instrument = assumptions.get("instrument_type")
    if instrument not in SUPPORTED_INSTRUMENT_TYPES:
        errors.append("instrument_type must be linear_spot or linear_perpetual")
    for field in ("venue", "quote_currency"):
        if not isinstance(assumptions.get(field), str) or not assumptions[field].strip():
            errors.append(f"{field} must be a non-empty string")
    for field in ("entry_fee_liquidity", "exit_fee_liquidity"):
        if assumptions.get(field) not in {"MAKER", "TAKER", "OTHER_EXPLICIT"}:
            errors.append(f"{field} must be MAKER, TAKER or OTHER_EXPLICIT")
    if not isinstance(assumptions.get("fee_rate_source"), str) or not assumptions["fee_rate_source"].strip():
        errors.append("fee_rate_source must be a non-empty string")
    for field in (
        "entry_fee_bps", "exit_fee_bps", "entry_spread_bps",
        "exit_spread_bps", "entry_slippage_bps", "exit_slippage_bps",
    ):
        try:
            _decimal(assumptions.get(field), field, nonnegative=True)
        except ValueError as exc:
            errors.append(str(exc))
    if assumptions.get("spread_input_semantics") != "ONE_LEG_ADVERSE_BPS":
        errors.append("spread_input_semantics must be ONE_LEG_ADVERSE_BPS")
    if assumptions.get("slippage_source") not in {"CONFIGURED_ESTIMATE", "OBSERVED_FILL"}:
        errors.append("slippage_source must be CONFIGURED_ESTIMATE or OBSERVED_FILL")
    funding_mode = assumptions.get("funding_mode")
    if instrument == "linear_spot" and funding_mode != "NOT_APPLICABLE":
        errors.append("linear_spot funding_mode must be NOT_APPLICABLE")
    if instrument == "linear_perpetual" and funding_mode not in {
        "OBSERVED_EVENTS", "CONFIGURED_RATE_PER_INTERVAL", "UNAVAILABLE",
    }:
        errors.append("linear_perpetual funding_mode is invalid")
    if funding_mode == "CONFIGURED_RATE_PER_INTERVAL":
        try:
            _decimal(assumptions.get("funding_rate_per_interval"), "funding_rate_per_interval")
            interval = int(assumptions.get("funding_interval_seconds"))
            if interval <= 0:
                raise ValueError
            _utc(assumptions.get("funding_first_event_at"), "funding_first_event_at")
        except (ValueError, TypeError):
            errors.append("configured funding requires rate, positive interval and first event time")
    if assumptions.get("gap_execution_mode") not in {
        "OBSERVED_FIRST_EXECUTABLE", "UNAVAILABLE",
    }:
        errors.append("gap_execution_mode must be OBSERVED_FIRST_EXECUTABLE or UNAVAILABLE")
    return errors


def _base_result(position: dict[str, Any], assumptions: dict[str, Any] | None) -> dict[str, Any]:
    hash_value = assumptions_hash(assumptions) if isinstance(assumptions, dict) else None
    position_id = str(position.get("position_id") or "")
    identity = None
    if position_id and hash_value:
        identity = hashlib.sha256(
            f"{position_id}|{FRICTION_MODEL_VERSION}|{hash_value}".encode()
        ).hexdigest()
    return {
        "assessment_id": identity,
        "position_id": position_id,
        "signal_id": position.get("signal_key"),
        "strategy": position.get("strategy_id"),
        "symbol": position.get("symbol"),
        "timeframe": position.get("timeframe"),
        "direction": position.get("side"),
        "entry_at": position.get("opened_at"),
        "exit_at": position.get("closed_at"),
        "entry_reference_price": position.get("entry_price"),
        "exit_reference_price": position.get("exit_price"),
        "stop_reference_price": position.get("stop_loss"),
        "close_reason": position.get("exit_reason"),
        "gross_pnl_quote": position.get("realized_pnl"),
        "gross_r": position.get("r_multiple"),
        "friction_model_version": FRICTION_MODEL_VERSION,
        "friction_model_status": "UNAVAILABLE",
        "friction_assumptions_hash": hash_value,
        "friction_calculated_at": position.get("closed_at"),
        "component_provenance": {},
        "errors": [],
    }


def assess_position_friction(
    position: dict[str, Any],
    assumptions: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a deterministic derived assessment; never mutate *position*."""
    result = _base_result(position, assumptions)
    if assumptions is None:
        result["errors"] = ["NET_FRICTION_MODEL_UNCONFIGURED"]
        return result

    assumption_errors = validate_assumptions(assumptions)
    unavailable = any("UNAVAILABLE" in str(assumptions.get(k)) for k in (
        "funding_mode", "gap_execution_mode",
    ))
    if assumption_errors:
        result["friction_model_status"] = "PARTIAL"
        result["errors"] = assumption_errors
        return result

    try:
        if position.get("status") not in _CLOSED:
            raise ValueError("position must be a supported closed lifecycle state")
        side = str(position.get("side") or "").upper()
        if side not in {"LONG", "SHORT"}:
            raise ValueError("direction must be LONG or SHORT")
        entry = _decimal(position.get("entry_price"), "entry_price")
        exit_price = _decimal(position.get("exit_price"), "exit_price")
        stop = _decimal(position.get("stop_loss"), "stop_loss")
        quantity = _decimal(position.get("position_size_preview"), "position_size_preview")
        gross_pnl = _decimal(position.get("realized_pnl"), "realized_pnl")
        gross_r = _decimal(position.get("r_multiple"), "r_multiple")
        if min(entry, exit_price, stop, quantity) <= 0:
            raise ValueError("prices and position size must be positive")
        risk_quote = abs(entry - stop) * quantity
        if risk_quote <= 0:
            raise ValueError("risk denominator must be positive")
        opened = _utc(position.get("opened_at"), "opened_at")
        closed = _utc(position.get("closed_at"), "closed_at")
        if closed < opened:
            raise ValueError("closed_at must not precede opened_at")
    except ValueError as exc:
        result["friction_model_status"] = "INVALID"
        result["errors"] = [str(exc)]
        return result

    component_quote: dict[str, Decimal] = {}
    provenance: dict[str, dict[str, Any]] = {}

    def adverse_bps(name: str, price: Decimal, field: str, source: str) -> None:
        bps = _decimal(assumptions[field], field, nonnegative=True)
        component_quote[name] = -(price * quantity * bps / _BPS)
        provenance[name] = {"source": source, "input_field": field, "unit": "bps"}

    adverse_bps(
        "entry_fee_effect", entry, "entry_fee_bps",
        f"{assumptions['fee_rate_source']}:{assumptions['entry_fee_liquidity']}",
    )
    adverse_bps(
        "exit_fee_effect", exit_price, "exit_fee_bps",
        f"{assumptions['fee_rate_source']}:{assumptions['exit_fee_liquidity']}",
    )
    adverse_bps("entry_spread_effect", entry, "entry_spread_bps", "configured_one_leg_adverse_spread")
    adverse_bps("exit_spread_effect", exit_price, "exit_spread_bps", "configured_one_leg_adverse_spread")
    adverse_bps("entry_slippage_effect", entry, "entry_slippage_bps", assumptions["slippage_source"])
    adverse_bps("exit_slippage_effect", exit_price, "exit_slippage_bps", assumptions["slippage_source"])

    funding_mode = assumptions["funding_mode"]
    funding = _ZERO
    if funding_mode == "NOT_APPLICABLE":
        provenance["funding_effect"] = {"source": "not_applicable", "boundary": "entry < event <= exit"}
    elif funding_mode == "UNAVAILABLE":
        unavailable = True
        provenance["funding_effect"] = {"source": "unavailable", "boundary": "entry < event <= exit"}
    elif funding_mode == "OBSERVED_EVENTS":
        events = position.get("funding_events")
        if not isinstance(events, list):
            unavailable = True
            provenance["funding_effect"] = {"source": "missing_observed_events", "boundary": "entry < event <= exit"}
        else:
            for event in events:
                event_at = _utc(event.get("at"), "funding event at")
                if not (opened < event_at <= closed):
                    continue
                rate = _decimal(event.get("rate"), "funding event rate")
                mark = _decimal(event.get("mark_price"), "funding event mark_price")
                signed = -(mark * quantity * rate) if side == "LONG" else mark * quantity * rate
                funding += signed
            provenance["funding_effect"] = {"source": "observed_events", "boundary": "entry < event <= exit"}
    else:
        rate = _decimal(assumptions["funding_rate_per_interval"], "funding_rate_per_interval")
        interval = int(assumptions["funding_interval_seconds"])
        event_at = _utc(assumptions["funding_first_event_at"], "funding_first_event_at")
        while event_at <= opened:
            event_at += timedelta(seconds=interval)
        count = 0
        while event_at <= closed:
            count += 1
            event_at += timedelta(seconds=interval)
        per_event = -(entry * quantity * rate) if side == "LONG" else entry * quantity * rate
        funding = per_event * count
        provenance["funding_effect"] = {
            "source": "configured_rate_per_interval", "events": count,
            "boundary": "entry < event <= exit", "rate_unit": "decimal_per_interval",
        }
    component_quote["funding_effect"] = funding

    gap = _ZERO
    is_stop = position.get("status") == "STOP_LOSS_HIT"
    if not is_stop:
        provenance["gap_execution_effect"] = {"source": "not_applicable_non_stop"}
    elif assumptions["gap_execution_mode"] == "UNAVAILABLE":
        unavailable = True
        provenance["gap_execution_effect"] = {"source": "missing_first_executable_price"}
    else:
        try:
            executable = _decimal(
                position.get("gap_execution_reference_price"),
                "gap_execution_reference_price",
            )
            if executable <= 0:
                raise ValueError("gap_execution_reference_price must be positive")
            if side == "LONG" and executable < exit_price:
                gap = (executable - exit_price) * quantity
            elif side == "SHORT" and executable > exit_price:
                gap = (exit_price - executable) * quantity
            provenance["gap_execution_effect"] = {
                "source": "observed_first_executable_price",
                "reference_price": _decimal_text(executable),
                "separation": "gap is price displacement; exit slippage remains configured bps on lifecycle exit reference",
            }
        except ValueError:
            unavailable = True
            provenance["gap_execution_effect"] = {"source": "missing_first_executable_price"}
    component_quote["gap_execution_effect"] = gap

    component_names = (
        "entry_fee_effect", "exit_fee_effect", "entry_spread_effect",
        "exit_spread_effect", "entry_slippage_effect", "exit_slippage_effect",
        "funding_effect", "gap_execution_effect",
    )
    total_quote = sum((component_quote[name] for name in component_names), _ZERO)
    total_r = total_quote / risk_quote
    net_pnl = gross_pnl + total_quote
    net_r = gross_r + total_r
    for name in component_names:
        result[f"{name}_quote"] = _decimal_text(component_quote[name])
        result[f"{name}_r"] = _decimal_text(component_quote[name] / risk_quote)
    result.update({
        "total_friction_effect_quote": _decimal_text(total_quote),
        "total_friction_effect_r": _decimal_text(total_r),
        "net_pnl_quote": _decimal_text(net_pnl),
        "net_r": _decimal_text(net_r),
        "gross_pnl_quote": _decimal_text(gross_pnl),
        "gross_r": _decimal_text(gross_r),
        "component_provenance": provenance,
        "risk_denominator_quote": _decimal_text(risk_quote),
    })
    if unavailable:
        result["friction_model_status"] = "PARTIAL"
        result["errors"] = ["mandatory friction evidence is unavailable"]
        result["net_pnl_quote"] = None
        result["net_r"] = None
    else:
        # v1 fee and spread rates are configured assumptions, so even when
        # funding/gap/fills are observed the combined assessment is estimated.
        # COMPLETE_OBSERVED is reserved for a future all-observed input contract.
        result["friction_model_status"] = "COMPLETE_ESTIMATED"
    return result


def aggregate_net_metrics(assessments: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(assessments)
    complete = [r for r in rows if r.get("friction_model_status") in COMPLETE_STATUSES]
    partial = [r for r in rows if r.get("friction_model_status") not in COMPLETE_STATUSES]
    result: dict[str, Any] = {
        "net_assessed_closed_count": len(rows),
        "net_complete_closed_count": len(complete),
        "net_incomplete_closed_count": len(partial),
        "net_sample_status": "NO_SAMPLE" if not complete else "COMPLETE_SAMPLE",
    }
    if not complete:
        result.update({
            "net_profit_factor": None, "net_profit_factor_status": "NO_SAMPLE",
            "net_expectancy_r": None, "net_average_r": None,
            "mean_friction_r": None, "median_friction_r": None,
            "total_friction_r": None,
        })
        return result
    net_r = [_decimal(r["net_r"], "net_r") for r in complete]
    friction_r = [_decimal(r["total_friction_effect_r"], "friction") for r in complete]
    wins = sum((r for r in net_r if r > 0), _ZERO)
    losses = abs(sum((r for r in net_r if r < 0), _ZERO))
    if losses == 0:
        pf, pf_status = (None, "INFINITE") if wins > 0 else (None, "NO_SAMPLE")
    else:
        pf, pf_status = (_decimal_text(wins / losses), "FINITE")
    result.update({
        "net_profit_factor": pf,
        "net_profit_factor_status": pf_status,
        "net_expectancy_r": _decimal_text(sum(net_r, _ZERO) / len(net_r)),
        "net_average_r": _decimal_text(sum(net_r, _ZERO) / len(net_r)),
        "mean_friction_r": _decimal_text(sum(friction_r, _ZERO) / len(friction_r)),
        "median_friction_r": _decimal_text(Decimal(str(median(friction_r)))),
        "total_friction_r": _decimal_text(sum(friction_r, _ZERO)),
    })
    for prefix in ("fee", "spread", "slippage", "funding", "gap"):
        if prefix in {"fee", "spread", "slippage"}:
            keys = [f"entry_{prefix}_effect_r", f"exit_{prefix}_effect_r"]
        else:
            keys = [f"{prefix}_effect_r" if prefix != "gap" else "gap_execution_effect_r"]
        total = sum((_decimal(r[k], k) for r in complete for k in keys), _ZERO)
        result[f"{prefix}_effect_r"] = _decimal_text(total)
    return result


def is_p1_03_trusted(
    position: dict[str, Any], assessment: dict[str, Any], manifest: dict[str, Any] | None,
) -> bool:
    if not manifest or not all(manifest.get(k) for k in NET_FRICTION_ACTIVATION_FIELDS):
        return False
    try:
        opened = _utc(position.get("opened_at"), "opened_at")
        activated = _utc(manifest["net_friction_trusted_cohort_start_at"], "activation")
        closed_bar_activated = _utc(
            manifest.get("closed_bar_trusted_cohort_start_at"), "closed-bar activation",
        )
    except ValueError:
        return False
    excluded_ids = {
        str(item.get("position_id") or "")
        for item in manifest.get("exclusions", []) if isinstance(item, dict)
    }
    return bool(
        opened >= activated
        and opened >= closed_bar_activated
        and str(position.get("position_id") or "") not in excluded_ids
        and position.get("signal_bar_contract_version") == "closed_bar_v1"
        and assessment.get("friction_model_version") == FRICTION_MODEL_VERSION
        and assessment.get("friction_model_status") in COMPLETE_STATUSES
        and assessment.get("friction_assumptions_hash") == manifest.get("net_friction_assumptions_hash")
        and manifest.get("net_friction_model_version") == FRICTION_MODEL_VERSION
    )


def _activation_metadata(
    start_at: str, run_id: str, commit: str, assumptions_hash_value: str,
) -> dict[str, str]:
    start = _utc(start_at, "net_friction_trusted_cohort_start_at").isoformat(timespec="seconds")
    if not run_id or not str(run_id).strip():
        raise ValueError("net friction activation run id must be non-empty")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", str(commit)):
        raise ValueError("net friction activation commit must be a full 40-character hash")
    if not re.fullmatch(r"[0-9a-f]{64}", str(assumptions_hash_value)):
        raise ValueError("net friction assumptions hash must be a lowercase SHA-256")
    return {
        "net_friction_trusted_cohort_start_at": start,
        "net_friction_trusted_cohort_rule_version": FRICTION_MODEL_VERSION,
        "net_friction_trusted_cohort_start_run_id": str(run_id).strip(),
        "net_friction_trusted_cohort_start_commit": str(commit).lower(),
        "net_friction_model_version": FRICTION_MODEL_VERSION,
        "net_friction_assumptions_hash": str(assumptions_hash_value),
    }


def activate_net_friction_trusted_cohort(
    manifest_path: str, *, start_at: str, run_id: str, commit: str,
    assumptions_hash_value: str,
) -> NetFrictionActivationResult:
    metadata = _activation_metadata(start_at, run_id, commit, assumptions_hash_value)
    try:
        with open(manifest_path) as handle:
            manifest = json.load(handle)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("exclusions"), list):
            raise ValueError("invalid overlap exclusion manifest")
        present = [k for k in NET_FRICTION_ACTIVATION_FIELDS if k in manifest]
        if present:
            if len(present) != len(NET_FRICTION_ACTIVATION_FIELDS):
                raise ValueError("partial net friction activation metadata")
            current = {k: manifest[k] for k in NET_FRICTION_ACTIVATION_FIELDS}
            if current == metadata:
                return NetFrictionActivationResult(
                    "ALREADY_ACTIVE_SAME_METADATA", manifest_path, metadata,
                )
            return NetFrictionActivationResult(
                "CONFLICTING_ACTIVATION", manifest_path, current,
                "net friction cohort is already active with different metadata",
            )
        updated = dict(manifest)
        updated.update(metadata)
        directory = os.path.dirname(os.path.abspath(manifest_path))
        fd, temporary = tempfile.mkstemp(prefix=".net-friction-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(updated, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, manifest_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return NetFrictionActivationResult("ACTIVATED", manifest_path, metadata)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return NetFrictionActivationResult("INVALID", manifest_path, metadata, str(exc))
