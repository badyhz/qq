from __future__ import annotations

from copy import deepcopy

import pytest

from core.paper_trading.net_friction import validate_assumptions_for_activation
from scripts.build_p1_03_weak_short_assumptions_package import (
    DEFAULT_SYMBOLS,
    build_package,
)


def readiness():
    per_symbol = {}
    for index, symbol in enumerate(DEFAULT_SYMBOLS, 1):
        per_symbol[symbol] = {
            "symbol_readiness": "READY",
            "valid_book_snapshot_count": 349,
            "valid_depth_snapshot_count": 346,
            "p95_one_leg_spread_bps": str(index),
            "p90_buy_impact_bps_by_notional": {
                "1000": str(index + 0.1),
                "5000": str(index + 0.2),
                "10000": str(index + 0.3),
            },
            "p90_sell_impact_bps_by_notional": {
                "1000": str(index + 0.4),
                "5000": str(index + 0.5),
                "10000": str(index + 0.6),
            },
            "funding_event_count": 48,
            "funding_continuity_resolved": True,
            "funding_conflict_count": 0,
        }
    return {
        "evidence_version": "friction_evidence_v1",
        "status": "READY_FOR_HUMAN_REVIEW",
        "observation_calendar_days": 16,
        "actual_account_fee_tier": "UNVERIFIED",
        "assumptions_approved": False,
        "p1_03_cohort_activated": False,
        "prospective_stops": {
            "prospective_stop_count": 418,
            "prospective_stop_with_gap_evidence": 418,
            "prospective_stop_missing_gap_evidence": 0,
            "prospective_gap_coverage_status": "COMPLETE",
        },
        "per_symbol": per_symbol,
    }


def test_missing_fee_inputs_fails_closed_without_assumptions_candidates():
    result = build_package(readiness())
    assert result["package_status"] == "BLOCKED_FEE_TIER_UNVERIFIED"
    assert result["candidates"] == []
    assert "ACTUAL_ACCOUNT_FEE_RATE_UNVERIFIED" in result["fee_input_blockers"]
    assert "FEE_RATE_SOURCE_UNVERIFIED" in result["fee_input_blockers"]
    assert result["cohort_activation_performed"] is False


def test_explicit_fees_generate_three_activation_valid_candidates():
    result = build_package(
        readiness(),
        entry_fee_bps="5",
        exit_fee_bps="5",
        fee_rate_source="HUMAN_CONFIRMED_TEST_FIXTURE",
    )
    assert result["package_status"] == "READY_FOR_HUMAN_ASSUMPTIONS_REVIEW"
    assert len(result["candidates"]) == 3
    assert result["fee_input_blockers"] == []
    for candidate in result["candidates"]:
        assert candidate["activation_validation_errors"] == []
        assert validate_assumptions_for_activation(candidate["assumptions"]) == []
        assert len(candidate["assumptions_hash"]) == 64
        assert candidate["candidate_status"] == "READY_FOR_HUMAN_ASSUMPTIONS_REVIEW"


def test_short_entry_uses_sell_impact_and_exit_uses_buy_impact():
    result = build_package(
        readiness(),
        notional_bands=("1000",),
        entry_fee_bps="5",
        exit_fee_bps="5",
        fee_rate_source="fixture",
    )
    candidate = result["candidates"][0]["assumptions"]
    xrp = candidate["profiles"]["WEAK_SHORT_XRPUSDT_1000USDT"]
    assert xrp["entry_slippage_bps"] == "1.4"
    assert xrp["exit_slippage_bps"] == "1.1"
    assert xrp["entry_spread_bps"] == "1"
    assert xrp["exit_spread_bps"] == "1"
    assert xrp["funding_mode"] == "OBSERVED_EVENTS"
    assert xrp["gap_execution_mode"] == "OBSERVED_FIRST_EXECUTABLE"


def test_each_symbol_gets_exact_perpetual_mapping_and_own_profile():
    result = build_package(
        readiness(),
        notional_bands=("5000",),
        entry_fee_bps="4",
        exit_fee_bps="5",
        fee_rate_source="fixture",
        entry_fee_liquidity="MAKER",
        exit_fee_liquidity="TAKER",
    )
    assumptions = result["candidates"][0]["assumptions"]
    assert set(assumptions["active_symbol_mapping"]) == set(DEFAULT_SYMBOLS)
    for symbol in DEFAULT_SYMBOLS:
        mapping = assumptions["active_symbol_mapping"][symbol]
        assert mapping["venue"] == "binance"
        assert mapping["instrument_type"] == "linear_perpetual"
        profile = assumptions["profiles"][mapping["profile"]]
        assert profile["maximum_supported_notional_quote"] == "5000"
        assert profile["entry_fee_liquidity"] == "MAKER"
        assert profile["exit_fee_liquidity"] == "TAKER"


def test_not_ready_report_is_rejected():
    report = readiness()
    report["status"] = "MORE_DATA"
    with pytest.raises(ValueError, match="not READY_FOR_HUMAN_REVIEW"):
        build_package(report)


def test_missing_gap_evidence_is_rejected():
    report = readiness()
    report["prospective_stops"]["prospective_stop_missing_gap_evidence"] = 1
    with pytest.raises(ValueError, match="gap evidence is incomplete"):
        build_package(report)


def test_symbol_funding_conflict_is_rejected():
    report = readiness()
    report["per_symbol"]["ARBUSDT"]["funding_conflict_count"] = 1
    with pytest.raises(ValueError, match="funding conflicts are nonzero"):
        build_package(report)


def test_missing_band_depth_evidence_is_rejected():
    report = readiness()
    del report["per_symbol"]["DOGEUSDT"]["p90_buy_impact_bps_by_notional"]["10000"]
    with pytest.raises(ValueError, match="no p90 depth evidence"):
        build_package(report)


def test_existing_activation_or_approval_is_rejected():
    approved = readiness()
    approved["assumptions_approved"] = True
    with pytest.raises(ValueError, match="already approved"):
        build_package(approved)

    active = readiness()
    active["p1_03_cohort_activated"] = True
    with pytest.raises(ValueError, match="already active"):
        build_package(active)
