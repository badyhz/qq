#!/usr/bin/env python3
"""Build a human-review P1-03 assumptions proposal for weak_short_watch.

This tool is deliberately read-only with respect to strategy state and cohort
activation. It consumes the already-derived friction evidence readiness report
and converts mature XRP/ARB/DOGE evidence into one candidate assumptions object
per supported diagnostic notional band.

Evidence-derived policy is frozen for this proposal version:
- entry/exit spread: per-symbol p95 one-leg adverse spread;
- SHORT entry slippage estimate: per-symbol p90 SELL book impact;
- SHORT exit slippage estimate: per-symbol p90 BUY book impact;
- funding: OBSERVED_EVENTS only;
- stop gap execution: OBSERVED_FIRST_EXECUTABLE only;
- notional boundary: the selected diagnostic band;
- actual account fee rates are never guessed.

Fee evidence must always be supplied explicitly at runtime with provenance.
For example, a human-confirmed Binance USD-M regular-user taker schedule can be
represented as ``--entry-fee-bps 5 --exit-fee-bps 5`` with a descriptive
``--fee-rate-source`` value. Optional BNB/VIP discounts must never be assumed
unless they are explicitly confirmed in the fee source used for that run.

No order, account, secret, Testnet, Live, deployment or cohort activation code
exists here. A candidate can become READY_FOR_HUMAN_ASSUMPTIONS_REVIEW only when
explicit fee inputs are supplied and the existing net_friction_v1 activation
validator accepts the generated assumptions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from core.paper_trading.net_friction import (
    FRICTION_MODEL_VERSION,
    assumptions_hash,
    validate_assumptions_for_activation,
)

PACKAGE_VERSION = "p1_03_weak_short_assumptions_proposal_v1"
STRATEGY_ID = "weak_short_watch"
DEFAULT_SYMBOLS = ("XRPUSDT", "ARBUSDT", "DOGEUSDT")
DEFAULT_NOTIONAL_BANDS = ("1000", "5000", "10000")


def _decimal_text(value: Any, field: str) -> str:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field} is unavailable")
    try:
        number = float(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if number < 0 or number != number or number in {float("inf"), float("-inf")}:
        raise ValueError(f"{field} must be finite and nonnegative")
    text = format(number, ".12f").rstrip("0").rstrip(".")
    return text or "0"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("readiness report must be a JSON object")
    return value


def _normalize_bands(readiness: dict[str, Any], requested: Iterable[str] | None) -> tuple[str, ...]:
    if requested:
        bands = tuple(str(item) for item in requested)
    else:
        configured = (
            readiness.get("diagnostic_notional_bands")
            or readiness.get("targets", {}).get("diagnostic_notional_bands")
        )
        bands = tuple(str(item) for item in configured) if configured else DEFAULT_NOTIONAL_BANDS
    if not bands or any(not band.strip() for band in bands):
        raise ValueError("at least one notional band is required")
    return bands


def _extract_symbol_evidence(readiness: dict[str, Any], symbol: str, bands: tuple[str, ...]) -> dict[str, Any]:
    per_symbol = readiness.get("per_symbol")
    if not isinstance(per_symbol, dict) or symbol not in per_symbol:
        raise ValueError(f"missing readiness evidence for {symbol}")
    row = per_symbol[symbol]
    if not isinstance(row, dict):
        raise ValueError(f"invalid readiness evidence for {symbol}")
    if row.get("symbol_readiness") != "READY":
        raise ValueError(f"{symbol} is not READY")
    if row.get("funding_continuity_resolved") is not True:
        raise ValueError(f"{symbol} funding continuity is not resolved")
    if int(row.get("funding_conflict_count") or 0) != 0:
        raise ValueError(f"{symbol} funding conflicts are nonzero")

    spread = _decimal_text(row.get("p95_one_leg_spread_bps"), f"{symbol} p95 spread")
    buy_map = row.get("p90_buy_impact_bps_by_notional")
    sell_map = row.get("p90_sell_impact_bps_by_notional")
    if not isinstance(buy_map, dict) or not isinstance(sell_map, dict):
        raise ValueError(f"{symbol} p90 impact maps are unavailable")

    by_band: dict[str, Any] = {}
    for band in bands:
        if band not in buy_map or band not in sell_map:
            raise ValueError(f"{symbol} has no p90 depth evidence for notional {band}")
        by_band[band] = {
            "entry_short_sell_p90_book_impact_bps": _decimal_text(
                sell_map.get(band), f"{symbol} sell impact {band}"
            ),
            "exit_short_buy_p90_book_impact_bps": _decimal_text(
                buy_map.get(band), f"{symbol} buy impact {band}"
            ),
        }

    return {
        "symbol": symbol,
        "valid_book_snapshot_count": int(row.get("valid_book_snapshot_count") or 0),
        "valid_depth_snapshot_count": int(row.get("valid_depth_snapshot_count") or 0),
        "p95_one_leg_spread_bps": spread,
        "funding_event_count": int(row.get("funding_event_count") or 0),
        "funding_continuity_resolved": True,
        "funding_conflict_count": 0,
        "by_notional_band": by_band,
    }


def _fee_inputs(
    *, entry_fee_bps: str | None, exit_fee_bps: str | None,
    fee_rate_source: str | None, entry_fee_liquidity: str,
    exit_fee_liquidity: str,
) -> tuple[dict[str, str] | None, list[str]]:
    blockers: list[str] = []
    if entry_fee_bps is None or exit_fee_bps is None:
        blockers.append("ACTUAL_ACCOUNT_FEE_RATE_UNVERIFIED")
    if not fee_rate_source or not fee_rate_source.strip():
        blockers.append("FEE_RATE_SOURCE_UNVERIFIED")
    if blockers:
        return None, blockers
    return {
        "entry_fee_bps": _decimal_text(entry_fee_bps, "entry_fee_bps"),
        "exit_fee_bps": _decimal_text(exit_fee_bps, "exit_fee_bps"),
        "entry_fee_liquidity": entry_fee_liquidity,
        "exit_fee_liquidity": exit_fee_liquidity,
        "fee_rate_source": fee_rate_source.strip(),
    }, []


def build_assumptions_candidate(
    *, band: str, evidence: dict[str, dict[str, Any]], fee: dict[str, str],
) -> dict[str, Any]:
    mappings: dict[str, Any] = {}
    profiles: dict[str, Any] = {}
    for symbol in sorted(evidence):
        row = evidence[symbol]
        profile_name = f"WEAK_SHORT_{symbol}_{band}USDT"
        impact = row["by_notional_band"][band]
        mappings[symbol] = {
            "profile": profile_name,
            "venue": "binance",
            "instrument_type": "linear_perpetual",
        }
        profiles[profile_name] = {
            **fee,
            "entry_spread_bps": row["p95_one_leg_spread_bps"],
            "exit_spread_bps": row["p95_one_leg_spread_bps"],
            "entry_slippage_bps": impact["entry_short_sell_p90_book_impact_bps"],
            "exit_slippage_bps": impact["exit_short_buy_p90_book_impact_bps"],
            "spread_input_semantics": "ONE_LEG_ADVERSE_BPS",
            "slippage_source": "CONFIGURED_ESTIMATE",
            "funding_mode": "OBSERVED_EVENTS",
            "gap_execution_mode": "OBSERVED_FIRST_EXECUTABLE",
            "maximum_supported_notional_quote": str(band),
            "maximum_supported_notional_currency": "USDT",
            "notional_measurement_version": "entry_exit_max_v1",
        }
    return {
        "friction_model_version": FRICTION_MODEL_VERSION,
        "quote_currency": "USDT",
        "active_symbol_mapping": mappings,
        "profiles": profiles,
    }


def build_package(
    readiness: dict[str, Any], *, symbols: tuple[str, ...] = DEFAULT_SYMBOLS,
    notional_bands: tuple[str, ...] | None = None,
    entry_fee_bps: str | None = None, exit_fee_bps: str | None = None,
    fee_rate_source: str | None = None,
    entry_fee_liquidity: str = "TAKER", exit_fee_liquidity: str = "TAKER",
) -> dict[str, Any]:
    if readiness.get("status") != "READY_FOR_HUMAN_REVIEW":
        raise ValueError("friction evidence readiness is not READY_FOR_HUMAN_REVIEW")
    if readiness.get("assumptions_approved") is True:
        raise ValueError("readiness unexpectedly reports assumptions already approved")
    if readiness.get("p1_03_cohort_activated") is True:
        raise ValueError("readiness unexpectedly reports P1-03 cohort already active")

    stop = readiness.get("prospective_stops")
    if not isinstance(stop, dict):
        raise ValueError("prospective stop summary is unavailable")
    if stop.get("prospective_gap_coverage_status") != "COMPLETE":
        raise ValueError("prospective stop gap coverage is not complete")
    if int(stop.get("prospective_stop_missing_gap_evidence") or 0) != 0:
        raise ValueError("prospective stop gap evidence is incomplete")

    bands = _normalize_bands(readiness, notional_bands)
    evidence = {symbol: _extract_symbol_evidence(readiness, symbol, bands) for symbol in symbols}
    fee, blockers = _fee_inputs(
        entry_fee_bps=entry_fee_bps,
        exit_fee_bps=exit_fee_bps,
        fee_rate_source=fee_rate_source,
        entry_fee_liquidity=entry_fee_liquidity,
        exit_fee_liquidity=exit_fee_liquidity,
    )

    candidates: list[dict[str, Any]] = []
    if fee is not None:
        for band in bands:
            assumptions = build_assumptions_candidate(band=band, evidence=evidence, fee=fee)
            activation_errors = validate_assumptions_for_activation(assumptions)
            candidates.append({
                "notional_band_quote": band,
                "assumptions": assumptions,
                "assumptions_hash": assumptions_hash(assumptions),
                "activation_validation_errors": activation_errors,
                "candidate_status": (
                    "READY_FOR_HUMAN_ASSUMPTIONS_REVIEW"
                    if not activation_errors else "INVALID_CANDIDATE"
                ),
            })

    ready = bool(candidates) and all(
        candidate["candidate_status"] == "READY_FOR_HUMAN_ASSUMPTIONS_REVIEW"
        for candidate in candidates
    )
    package_status = (
        "READY_FOR_HUMAN_ASSUMPTIONS_REVIEW"
        if ready else "BLOCKED_FEE_TIER_UNVERIFIED" if blockers else "INVALID_CANDIDATE"
    )
    return {
        "package_version": PACKAGE_VERSION,
        "strategy_id": STRATEGY_ID,
        "package_status": package_status,
        "source_evidence_version": readiness.get("evidence_version"),
        "source_readiness_status": readiness.get("status"),
        "observation_calendar_days": int(readiness.get("observation_calendar_days") or 0),
        "prospective_stop_count": int(stop.get("prospective_stop_count") or 0),
        "prospective_stop_with_gap_evidence": int(stop.get("prospective_stop_with_gap_evidence") or 0),
        "prospective_gap_coverage_status": stop.get("prospective_gap_coverage_status"),
        "source_actual_account_fee_tier": readiness.get("actual_account_fee_tier", "UNVERIFIED"),
        "fee_input_blockers": blockers,
        "fee_input": fee,
        "symbols": list(symbols),
        "notional_bands_quote": list(bands),
        "evidence_selection_policy": {
            "spread": "P95_ONE_LEG_ADVERSE_SPREAD_BPS",
            "short_entry_slippage": "P90_SELL_BOOK_IMPACT_BPS",
            "short_exit_slippage": "P90_BUY_BOOK_IMPACT_BPS",
            "funding": "OBSERVED_EVENTS",
            "gap_execution": "OBSERVED_FIRST_EXECUTABLE",
            "slippage_label": "CONFIGURED_ESTIMATE_FROM_BOOK_IMPACT_NOT_ACTUAL_FILL",
        },
        "symbol_evidence": evidence,
        "candidates": candidates,
        "human_approval_required": True,
        "cohort_activation_performed": False,
        "production_change_performed": False,
        "testnet_enabled": False,
        "live_enabled": False,
        "real_order_enabled": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build weak_short P1-03 assumptions proposal only")
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--notional-bands", default=",".join(DEFAULT_NOTIONAL_BANDS))
    parser.add_argument("--entry-fee-bps")
    parser.add_argument("--exit-fee-bps")
    parser.add_argument("--fee-rate-source")
    parser.add_argument("--entry-fee-liquidity", default="TAKER", choices=("MAKER", "TAKER", "OTHER_EXPLICIT"))
    parser.add_argument("--exit-fee-liquidity", default="TAKER", choices=("MAKER", "TAKER", "OTHER_EXPLICIT"))
    args = parser.parse_args(argv)

    readiness = _load_json(Path(args.readiness))
    package = build_package(
        readiness,
        symbols=tuple(item.strip().upper() for item in args.symbols.split(",") if item.strip()),
        notional_bands=tuple(item.strip() for item in args.notional_bands.split(",") if item.strip()),
        entry_fee_bps=args.entry_fee_bps,
        exit_fee_bps=args.exit_fee_bps,
        fee_rate_source=args.fee_rate_source,
        entry_fee_liquidity=args.entry_fee_liquidity,
        exit_fee_liquidity=args.exit_fee_liquidity,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "package_status": package["package_status"],
        "candidate_count": len(package["candidates"]),
        "human_approval_required": True,
        "cohort_activation_performed": False,
        "output": str(output),
    }, sort_keys=True))
    return 0 if package["package_status"] in {
        "READY_FOR_HUMAN_ASSUMPTIONS_REVIEW", "BLOCKED_FEE_TIER_UNVERIFIED"
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())