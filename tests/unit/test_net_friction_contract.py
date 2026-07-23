from __future__ import annotations

import hashlib
import json
import os
import subprocess
from copy import deepcopy
from decimal import Decimal

import pytest
import yaml

from core.paper_trading.net_friction import (
    FRICTION_MODEL_VERSION,
    activate_net_friction_trusted_cohort,
    aggregate_net_metrics,
    assess_position_friction,
    assumptions_hash,
    is_p1_03_trusted,
    validate_assumptions_for_activation,
)
from core.paper_trading.friction_evidence import (
    ATTRIBUTION_VERSION,
    EVIDENCE_VERSION,
    PROSPECTIVE_BOUNDARY_SOURCE,
    PROSPECTIVE_BOUNDARY_VERSION,
    EvidenceStore,
    attribute_position_funding,
    book_impact,
    build_depth_evidence,
    build_funding_evidence,
    build_funding_coverage_evidence,
    build_position_funding_attribution_evidence,
    build_readiness_report,
    build_top_of_book_evidence,
    collect_evidence_cycle,
    derive_prospective_boundary,
    evidence_id,
    load_evidence_config,
    payload_hash,
    regenerate_readiness,
    resolve_active_universe,
    stop_evidence_summary,
    write_readiness_report,
)


def assumptions(**overrides):
    profile = {
        "entry_fee_bps": "4", "exit_fee_bps": "4",
        "entry_fee_liquidity": "TAKER", "exit_fee_liquidity": "TAKER",
        "fee_rate_source": "configured_fixture",
        "entry_spread_bps": "1", "exit_spread_bps": "1",
        "entry_slippage_bps": "2", "exit_slippage_bps": "2",
        "spread_input_semantics": "ONE_LEG_ADVERSE_BPS",
        "slippage_source": "CONFIGURED_ESTIMATE",
        "funding_mode": "NOT_APPLICABLE",
        "gap_execution_mode": "OBSERVED_FIRST_EXECUTABLE",
        "maximum_supported_notional_quote": "1000",
        "maximum_supported_notional_currency": "USDT",
        "notional_measurement_version": "entry_exit_max_v1",
    }
    mapping = {
        "profile": "DEFAULT", "venue": "fixture_exchange",
        "instrument_type": "linear_spot",
    }
    root_fields = {"friction_model_version", "quote_currency", "active_symbol_mapping", "profiles"}
    for key, value in overrides.items():
        if key == "instrument_type":
            mapping[key] = value
        elif key == "venue":
            mapping[key] = value
        elif key in root_fields:
            continue
        else:
            profile[key] = value
    value = {
        "friction_model_version": "net_friction_v1",
        "quote_currency": "USDT",
        "active_symbol_mapping": {"BTCUSDT": mapping},
        "profiles": {"DEFAULT": profile},
    }
    for key in root_fields:
        if key in overrides:
            value[key] = overrides[key]
    return value


def position(**overrides):
    value = {
        "position_id": "PP_fixture",
        "signal_key": "sig-1",
        "strategy_id": "fixture_strategy",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "side": "LONG",
        "status": "TAKE_PROFIT_HIT",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "stop_loss": 95.0,
        "position_size_preview": 2.0,
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T09:00:00+00:00",
        "exit_reason": "take_profit triggered",
        "take_profit": 110.0,
        "lifecycle_mode": "future_only",
        "realized_pnl": 20.0,
        "r_multiple": 2.0,
        "signal_bar_contract_version": "closed_bar_v1",
    }
    value.update(overrides)
    if value["status"] == "STOP_LOSS_HIT" and "gap_execution_reference_price" in overrides:
        value.setdefault("exit_trigger_bar_open", value["gap_execution_reference_price"])
        value.setdefault("exit_trigger_bar_close_time", "2026-07-21T09:00:00+00:00")
        value.setdefault("nominal_stop_price", value["stop_loss"])
        value.setdefault("gap_execution_evidence_version", "stop_trigger_bar_open_v1")
    return value


def manifest(tmp_path):
    path = tmp_path / "paper_position_overlap_exclusions.json"
    path.write_text(json.dumps({
        "audit_rule_version": "cross_day_exposure_v1",
        "trusted_cohort_start_at": "2026-07-20T00:00:00+00:00",
        "exclusions": [{"position_id": f"old-{i}"} for i in range(200)],
        "closed_bar_trusted_cohort_start_at": "2026-07-20T12:00:00+00:00",
        "closed_bar_trusted_cohort_rule_version": "closed_bar_v1",
        "closed_bar_trusted_cohort_start_run_id": "old-run",
        "closed_bar_trusted_cohort_start_commit": "1" * 40,
    }, indent=2))
    return path


def D(result, key):
    return Decimal(result[key])


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_fees_are_adverse_for_long_and_short(side):
    p = position(side=side)
    if side == "SHORT":
        p.update(exit_price="90", realized_pnl="20", r_multiple="2")
    result = assess_position_friction(p, assumptions())
    assert D(result, "entry_fee_effect_quote") == Decimal("-0.08")
    expected_exit = Decimal("-0.088") if side == "LONG" else Decimal("-0.072")
    assert D(result, "exit_fee_effect_quote") == expected_exit


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_spread_is_adverse_for_long_and_short(side):
    p = position(side=side, exit_price="90" if side == "SHORT" else "110")
    result = assess_position_friction(p, assumptions())
    assert D(result, "entry_spread_effect_quote") < 0
    assert D(result, "exit_spread_effect_quote") < 0


@pytest.mark.parametrize("side", ["LONG", "SHORT"])
def test_slippage_is_adverse_for_long_and_short(side):
    p = position(side=side, exit_price="90" if side == "SHORT" else "110")
    result = assess_position_friction(p, assumptions())
    assert D(result, "entry_slippage_effect_quote") < 0
    assert D(result, "exit_slippage_effect_quote") < 0


@pytest.mark.parametrize(
    ("side", "rate", "expected_sign"),
    [("LONG", "0.001", -1), ("LONG", "-0.001", 1),
     ("SHORT", "0.001", 1), ("SHORT", "-0.001", -1)],
)
def test_observed_funding_direction(side, rate, expected_sign):
    p = position(side=side, funding_events=[{
        "symbol": "BTCUSDT", "funding_timestamp": "2026-07-21T08:00:00+00:00",
        "signed_funding_rate": rate, "mark_price": "105", "source": "fixture",
    }], funding_events_verified_complete=True)
    config = assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS")
    result = assess_position_friction(p, config)
    assert D(result, "funding_effect_quote").compare(Decimal("0")) == Decimal(expected_sign)


def test_multiple_funding_events_and_boundary_entry_excluded_exit_included():
    p = position(funding_events=[
        {"symbol": "BTCUSDT", "funding_timestamp": at, "signed_funding_rate": "0.001", "mark_price": "100", "source": "fixture"}
        for at in ["2026-07-21T00:00:00+00:00", "2026-07-21T04:00:00+00:00", "2026-07-21T09:00:00+00:00", "2026-07-21T10:00:00+00:00"]
    ], funding_events_verified_complete=True)
    result = assess_position_friction(
        p, assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS"),
    )
    assert D(result, "funding_effect_quote") == Decimal("-0.4")


def test_configured_funding_intervals_count_once():
    config = assumptions(
        instrument_type="linear_perpetual",
        funding_mode="CONFIGURED_RATE_BY_SYMBOL",
        funding_rate_by_symbol={"BTCUSDT": {
            "rate_per_interval": "0.001", "interval_seconds": 14400,
            "first_event_at": "2026-07-21T00:00:00+00:00", "source": "fixture",
        }},
    )
    result = assess_position_friction(position(), config)
    assert D(result, "funding_effect_quote") == Decimal("-0.4")
    assert result["component_provenance"]["funding_effect"]["events"] == 2


@pytest.mark.parametrize(
    ("side", "executable", "expected"),
    [("LONG", "90", "-10"), ("SHORT", "110", "-10")],
)
def test_stop_through_gap_is_direction_aware(side, executable, expected):
    p = position(
        side=side, status="STOP_LOSS_HIT", exit_price="95" if side == "LONG" else "105",
        stop_loss="95" if side == "LONG" else "105", realized_pnl="-10", r_multiple="-1",
        gap_execution_reference_price=executable, exit_reason="stop_loss triggered",
    )
    result = assess_position_friction(p, assumptions())
    assert D(result, "gap_execution_effect_quote") == Decimal(expected)


@pytest.mark.parametrize("side,executable", [("LONG", "95"), ("SHORT", "105")])
def test_no_stop_gap_is_zero(side, executable):
    p = position(
        side=side, status="STOP_LOSS_HIT", exit_price="95" if side == "LONG" else "105",
        stop_loss="95" if side == "LONG" else "105", realized_pnl="-10", r_multiple="-1",
        gap_execution_reference_price=executable,
    )
    assert D(assess_position_friction(p, assumptions()), "gap_execution_effect_quote") == 0


def test_gap_evidence_must_be_timezone_aware_and_formula_bound():
    base = dict(
        status="STOP_LOSS_HIT", exit_price="95", stop_loss="95",
        realized_pnl="-10", r_multiple="-1", gap_execution_reference_price="90",
        exit_trigger_bar_open="90", nominal_stop_price="95",
        gap_execution_evidence_version="stop_trigger_bar_open_v1",
    )
    naive = assess_position_friction(
        position(**base, exit_trigger_bar_close_time="2026-07-21T09:00:00"), assumptions(),
    )
    mismatch = assess_position_friction(position(**{
        **base, "exit_trigger_bar_open": "96",
        "exit_trigger_bar_close_time": "2026-07-21T09:00:00+00:00",
    }), assumptions())
    assert naive["friction_model_status"] == "PARTIAL"
    assert mismatch["friction_model_status"] == "PARTIAL"


@pytest.mark.parametrize("status", ["TAKE_PROFIT_HIT", "TIMEOUT_EXIT"])
def test_non_stop_close_has_no_invented_gap(status):
    result = assess_position_friction(position(status=status), assumptions())
    assert D(result, "gap_execution_effect_quote") == 0
    assert result["component_provenance"]["gap_execution_effect"]["source"] == "not_applicable_non_stop"


def test_net_and_r_equations_and_no_double_counting():
    result = assess_position_friction(position(), assumptions())
    components = [
        "entry_fee_effect_quote", "exit_fee_effect_quote",
        "entry_spread_effect_quote", "exit_spread_effect_quote",
        "entry_slippage_effect_quote", "exit_slippage_effect_quote",
        "funding_effect_quote", "gap_execution_effect_quote",
    ]
    total = sum((D(result, k) for k in components), Decimal("0"))
    assert total == D(result, "total_friction_effect_quote")
    assert D(result, "gross_pnl_quote") + total == D(result, "net_pnl_quote")
    assert D(result, "gross_r") + D(result, "total_friction_effect_r") == D(result, "net_r")
    assert len(result["component_provenance"]) == 8


def test_zero_risk_denominator_is_invalid():
    result = assess_position_friction(position(stop_loss="100"), assumptions())
    assert result["friction_model_status"] == "INVALID"
    assert result["net_r"] if "net_r" in result else None is None


def test_missing_mandatory_fee_is_partial_not_zero_cost():
    config = assumptions()
    del config["profiles"]["DEFAULT"]["entry_fee_bps"]
    result = assess_position_friction(position(), config)
    assert result["friction_model_status"] == "PARTIAL"
    assert "entry_fee_bps" in " ".join(result["errors"])


def test_missing_perpetual_funding_is_partial():
    result = assess_position_friction(
        position(), assumptions(instrument_type="linear_perpetual", funding_mode="UNAVAILABLE"),
    )
    assert result["friction_model_status"] == "PARTIAL"
    assert result["net_r"] is None


def test_spot_funding_not_applicable_is_complete():
    result = assess_position_friction(position(), assumptions())
    assert result["friction_model_status"] == "COMPLETE_ESTIMATED"
    assert D(result, "funding_effect_quote") == 0


def test_unsupported_instrument_fails_closed():
    result = assess_position_friction(position(), assumptions(instrument_type="inverse_perpetual"))
    assert result["friction_model_status"] == "PARTIAL"


def test_stop_without_bar_evidence_is_partial_not_zero():
    p = position(status="STOP_LOSS_HIT", exit_price="95", realized_pnl="-10", r_multiple="-1")
    result = assess_position_friction(p, assumptions())
    assert result["friction_model_status"] == "PARTIAL"
    assert result["net_r"] is None


def test_deterministic_repeat_and_serialization_round_trip():
    first = assess_position_friction(position(), assumptions())
    second = assess_position_friction(deepcopy(position()), deepcopy(assumptions()))
    assert first == second
    assert json.loads(json.dumps(first)) == first


def test_assumption_change_creates_new_identity():
    first = assess_position_friction(position(), assumptions(entry_fee_bps="4"))
    second = assess_position_friction(position(), assumptions(entry_fee_bps="5"))
    assert first["assessment_id"] != second["assessment_id"]
    assert first["friction_assumptions_hash"] != second["friction_assumptions_hash"]


def test_assumptions_hash_canonicalizes_numbers_and_key_order():
    left = assumptions(entry_fee_bps=4.0)
    right = dict(reversed(list(assumptions(entry_fee_bps="4").items())))
    assert assumptions_hash(left) == assumptions_hash(right)


def test_net_metrics_exclude_partial_and_use_net_r():
    a = assess_position_friction(position(position_id="a", realized_pnl="20", r_multiple="2"), assumptions())
    b = assess_position_friction(position(position_id="b", exit_price="95", realized_pnl="-10", r_multiple="-1", status="STOP_LOSS_HIT", gap_execution_reference_price="95"), assumptions())
    partial = assess_position_friction(position(position_id="c"), None)
    metrics = aggregate_net_metrics([a, b, partial])
    expected = (D(a, "net_r") + D(b, "net_r")) / 2
    assert metrics["net_expectancy_r"] is None
    assert Decimal(metrics["diagnostic_complete_subset_net_expectancy_r"]) == expected
    assert metrics["net_metrics_status"] == "INCOMPLETE_COVERAGE"
    assert metrics["net_complete_closed_count"] == 2
    assert metrics["net_incomplete_closed_count"] == 1


def test_unknown_symbol_fails_closed_with_mapping_diagnostics():
    result = assess_position_friction(position(symbol="ETHUSDT"), assumptions())
    assert result["friction_model_status"] == "INVALID"
    assert result["errors"] == ["SYMBOL_MAPPING_NOT_FOUND"]


def test_unknown_profile_and_symbol_case_fail_configuration_or_mapping():
    config = assumptions()
    config["active_symbol_mapping"]["BTCUSDT"]["profile"] = "MISSING"
    assert assess_position_friction(position(), config)["friction_model_status"] == "PARTIAL"
    assert assess_position_friction(position(symbol="btcusdt"), assumptions())["errors"] == [
        "SYMBOL_MAPPING_NOT_FOUND"
    ]


@pytest.mark.parametrize(
    "field,value,error",
    [("venue", "wrong", "POSITION_VENUE_MISMATCH"),
     ("instrument_type", "linear_perpetual", "POSITION_INSTRUMENT_TYPE_MISMATCH")],
)
def test_position_mapping_metadata_mismatch_is_invalid(field, value, error):
    result = assess_position_friction(position(**{field: value}), assumptions())
    assert result["friction_model_status"] == "INVALID"
    assert result["errors"] == [error]


def test_exact_symbol_mapping_and_notional_are_auditable():
    result = assess_position_friction(position(), assumptions())
    assert result["mapping_result"] == "EXACT_MATCH"
    assert result["configured_symbol"] == result["observed_symbol"] == "BTCUSDT"
    assert result["assessed_notional_quote"] == "220"
    assert result["notional_boundary_result"] == "WITHIN_BOUNDARY"


@pytest.mark.parametrize("quantity,exit_price", [("11", "100"), ("1", "1001")])
def test_notional_above_boundary_is_invalid(quantity, exit_price):
    result = assess_position_friction(
        position(position_size_preview=quantity, exit_price=exit_price), assumptions(),
    )
    assert result["friction_model_status"] == "INVALID"
    assert result["notional_boundary_result"] == "EXCEEDED"
    assert result["errors"] == ["NOTIONAL_EXCEEDS_APPROVED_BOUNDARY"]


def test_notional_boundary_is_inclusive():
    result = assess_position_friction(
        position(position_size_preview="10", exit_price="100"), assumptions(),
    )
    assert result["friction_model_status"] == "COMPLETE_ESTIMATED"
    assert result["assessed_notional_quote"] == "1000"


def test_descriptive_notional_limit_is_rejected():
    result = assess_position_friction(
        position(), assumptions(maximum_supported_notional_quote="about 1000"),
    )
    assert result["friction_model_status"] == "PARTIAL"


def test_unsupported_quote_currency_is_rejected():
    result = assess_position_friction(position(), assumptions(quote_currency="USD"))
    assert result["friction_model_status"] == "PARTIAL"
    assert "notional currency must match" in " ".join(result["errors"])


def test_global_scalar_funding_is_diagnostic_only_and_activation_rejected():
    config = assumptions(
        instrument_type="linear_perpetual", funding_mode="CONFIGURED_RATE_PER_INTERVAL",
        funding_rate_per_interval="0.001", funding_interval_seconds=28800,
        funding_first_event_at="2026-07-21T00:00:00+00:00",
    )
    result = assess_position_friction(position(), config)
    assert result["friction_model_status"] == "PARTIAL"
    assert result["funding_trusted"] is False
    assert validate_assumptions_for_activation(config)


def _observed_event(**overrides):
    value = {
        "symbol": "BTCUSDT", "funding_timestamp": "2026-07-21T08:00:00+00:00",
        "signed_funding_rate": "0.001", "mark_price": "100", "source": "fixture",
    }
    value.update(overrides)
    return value


def test_observed_funding_requires_completeness_proof_even_when_empty():
    config = assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS")
    incomplete = assess_position_friction(position(funding_events=[]), config)
    complete_zero = assess_position_friction(
        position(funding_events=[], funding_events_verified_complete=True), config,
    )
    assert incomplete["friction_model_status"] == "PARTIAL"
    assert complete_zero["friction_model_status"] == "COMPLETE_ESTIMATED"


def test_observed_funding_rejects_wrong_symbol():
    config = assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS")
    result = assess_position_friction(position(
        funding_events=[_observed_event(symbol="ETHUSDT")],
        funding_events_verified_complete=True,
    ), config)
    assert result["friction_model_status"] == "INVALID"
    assert result["errors"] == ["FUNDING_EVENT_SYMBOL_MISMATCH"]


def test_malformed_observed_funding_event_fails_closed_without_exception():
    config = assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS")
    result = assess_position_friction(position(
        funding_events=["malformed"], funding_events_verified_complete=True,
    ), config)
    assert result["friction_model_status"] == "INVALID"
    assert result["funding_trusted"] is False
    assert result["errors"] == ["FUNDING_EVENT_MUST_BE_OBJECT"]


def test_observed_funding_deduplicates_identical_timestamp():
    config = assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS")
    event = _observed_event()
    result = assess_position_friction(position(
        funding_events=[event, deepcopy(event)], funding_events_verified_complete=True,
    ), config)
    assert D(result, "funding_effect_quote") == Decimal("-0.2")
    assert result["component_provenance"]["funding_effect"]["events"] == 1


def test_observed_funding_rejects_conflicting_duplicate_timestamp():
    config = assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS")
    result = assess_position_friction(position(
        funding_events=[_observed_event(), _observed_event(signed_funding_rate="0.002")],
        funding_events_verified_complete=True,
    ), config)
    assert result["friction_model_status"] == "INVALID"
    assert result["errors"] == ["CONFLICTING_DUPLICATE_FUNDING_EVENT"]


def test_symbol_funding_configuration_must_cover_position_symbol():
    config = assumptions(
        instrument_type="linear_perpetual", funding_mode="CONFIGURED_RATE_BY_SYMBOL",
        funding_rate_by_symbol={"ETHUSDT": {
            "rate_per_interval": "0.001", "interval_seconds": 28800,
            "first_event_at": "2026-07-21T00:00:00+00:00", "source": "fixture",
        }},
    )
    result = assess_position_friction(position(), config)
    assert result["friction_model_status"] == "INVALID"
    assert result["errors"] == ["SYMBOL_FUNDING_RATE_NOT_CONFIGURED"]


@pytest.mark.parametrize(
    "side,rate,sign",
    [("LONG", "0.001", -1), ("SHORT", "0.001", 1),
     ("LONG", "-0.001", 1), ("SHORT", "-0.001", -1)],
)
def test_symbol_configured_funding_direction(side, rate, sign):
    config = assumptions(
        instrument_type="linear_perpetual", funding_mode="CONFIGURED_RATE_BY_SYMBOL",
        funding_rate_by_symbol={"BTCUSDT": {
            "rate_per_interval": rate, "interval_seconds": 14400,
            "first_event_at": "2026-07-21T00:00:00+00:00", "source": "fixture",
        }},
    )
    result = assess_position_friction(position(side=side), config)
    assert D(result, "funding_effect_quote").compare(Decimal("0")) == Decimal(sign)


def test_outcome_selection_bias_suppresses_trusted_net_result():
    winner = assess_position_friction(position(position_id="win"), assumptions())
    stop = assess_position_friction(position(
        position_id="stop", status="STOP_LOSS_HIT", exit_reason="stop_loss triggered",
        exit_price="95", realized_pnl="-10", r_multiple="-1",
    ), assumptions())
    metrics = aggregate_net_metrics([winner, stop])
    assert metrics["net_metrics_status"] == "INCOMPLETE_COVERAGE"
    assert metrics["selection_bias_warning"] == "OUTCOME_SELECTION_BIAS_DETECTED"
    assert metrics["net_profit_factor"] is None
    assert metrics["net_expectancy_r"] is None
    assert metrics["excluded_by_close_reason"] == {"stop_loss triggered": 1}
    assert metrics["diagnostic_complete_subset_count"] == 1


def test_full_coverage_allows_trusted_net_result():
    rows = [assess_position_friction(position(position_id=str(i)), assumptions()) for i in range(2)]
    metrics = aggregate_net_metrics(rows)
    assert metrics["net_metrics_status"] == "COMPLETE_ESTIMATED"
    assert metrics["net_coverage_ratio"] == "1"
    assert metrics["net_expectancy_r"] is not None


def test_reproduced_679_denominator_blocks_survivor_only_headline():
    complete = assess_position_friction(position(), assumptions())
    partial_stop = assess_position_friction(position(
        status="STOP_LOSS_HIT", exit_reason="stop_loss triggered", exit_price="95",
        realized_pnl="-10", r_multiple="-1",
    ), assumptions())
    metrics = aggregate_net_metrics([deepcopy(complete) for _ in range(327)] + [
        deepcopy(partial_stop) for _ in range(352)
    ])
    assert metrics["eligible_closed_count"] == 679
    assert metrics["complete_assessment_count"] == 327
    assert metrics["partial_assessment_count"] == 352
    assert metrics["net_profit_factor"] is None
    assert metrics["net_expectancy_r"] is None
    assert metrics["net_metrics_status"] == "INCOMPLETE_COVERAGE"
    assert metrics["selection_bias_warning"] == "OUTCOME_SELECTION_BIAS_DETECTED"


def test_empty_net_sample_is_explicit():
    metrics = aggregate_net_metrics([assess_position_friction(position(), None)])
    assert metrics["net_sample_status"] == "NO_SAMPLE"
    assert metrics["net_profit_factor"] is None


def test_activation_repeat_and_conflict_are_hash_stable(tmp_path):
    path = manifest(tmp_path)
    kwargs = dict(
        start_at="2026-07-21T10:00:00+00:00", run_id="run-1", commit="a" * 40,
        assumptions_hash_value=assumptions_hash(assumptions()),
    )
    first = activate_net_friction_trusted_cohort(str(path), **kwargs)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    repeat = activate_net_friction_trusted_cohort(str(path), **kwargs)
    assert first.status == "ACTIVATED"
    assert repeat.status == "ALREADY_ACTIVE_SAME_METADATA"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    conflict = activate_net_friction_trusted_cohort(str(path), **{**kwargs, "run_id": "run-2"})
    assert conflict.status == "CONFLICTING_ACTIVATION"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert len(json.loads(path.read_text())["exclusions"]) == 200


def activated_manifest(tmp_path):
    path = manifest(tmp_path)
    config = assumptions()
    activate_net_friction_trusted_cohort(
        str(path), start_at="2026-07-21T10:00:00+00:00", run_id="run-1",
        commit="a" * 40, assumptions_hash_value=assumptions_hash(config),
    )
    return json.loads(path.read_text()), config


def test_pre_activation_position_is_not_trusted(tmp_path):
    m, config = activated_manifest(tmp_path)
    p = position(opened_at="2026-07-21T09:59:59+00:00")
    assert not is_p1_03_trusted(p, assess_position_friction(p, config), m)


def test_post_activation_complete_position_is_trusted(tmp_path):
    m, config = activated_manifest(tmp_path)
    p = position(
        opened_at="2026-07-21T10:00:00+00:00",
        closed_at="2026-07-21T11:00:00+00:00",
    )
    assert is_p1_03_trusted(p, assess_position_friction(p, config), m)


def test_overlap_excluded_position_cannot_enter_p1_03(tmp_path):
    m, config = activated_manifest(tmp_path)
    p = position(
        position_id="old-1",
        opened_at="2026-07-21T10:00:00+00:00",
        closed_at="2026-07-21T11:00:00+00:00",
    )
    assert not is_p1_03_trusted(p, assess_position_friction(p, config), m)


@pytest.mark.parametrize("mutation", ["closed_bar", "model", "hash", "partial"])
def test_incomplete_contracts_are_not_trusted(tmp_path, mutation):
    m, config = activated_manifest(tmp_path)
    p = position(
        opened_at="2026-07-21T10:00:00+00:00",
        closed_at="2026-07-21T11:00:00+00:00",
    )
    assessment = assess_position_friction(p, config)
    if mutation == "closed_bar":
        p["signal_bar_contract_version"] = "legacy_missing"
    elif mutation == "model":
        assessment["friction_model_version"] = None
    elif mutation == "hash":
        assessment["friction_assumptions_hash"] = "0" * 64
    else:
        assessment["friction_model_status"] = "PARTIAL"
    assert not is_p1_03_trusted(p, assessment, m)


def test_gross_input_is_never_mutated():
    p = position()
    before = deepcopy(p)
    assess_position_friction(p, assumptions())
    assert p == before
    assert p["realized_pnl"] == 20.0
    assert p["r_multiple"] == 2.0


def test_calculation_anchor_is_deterministic_closed_at():
    result = assess_position_friction(position(), assumptions())
    assert result["friction_calculated_at"] == position()["closed_at"]
    assert result["friction_model_version"] == FRICTION_MODEL_VERSION


def test_scorecard_keeps_gross_and_adds_net_payload(tmp_path, monkeypatch):
    from scripts import run_paper_performance_scorecard as runner

    report = tmp_path / "reports"
    report.mkdir()
    p = position(
        date="2026-07-21", source="real_public_readonly",
        quarantine_status="CLEAN",
    )
    (report / "2026-07-21_paper_position_ledger.jsonl").write_text(json.dumps(p) + "\n")
    config_path = tmp_path / "friction.json"
    config_path.write_text(json.dumps(assumptions()))
    monkeypatch.setattr(runner, "REPORT_DIR", str(report))
    monkeypatch.setattr(
        "sys.argv",
        ["scorecard", "--date", "2026-07-21", "--output-dir", str(report),
         "--friction-config", str(config_path)],
    )
    assert runner.main() == 0
    payload = json.loads((report / "2026-07-21_paper_performance_scorecard.json").read_text())
    assert payload["global_metrics"]["profit_factor"] == "inf" or payload["global_metrics"]["profit_factor"] == float("inf")
    assert payload["global_metrics"]["expectancy_r"] == 2.0
    assert payload["net_friction"]["gross_expectancy_r"] == 2.0
    assert payload["net_friction"]["complete_metrics"]["net_complete_closed_count"] == 1
    assert len(payload["net_friction"]["assessments"]) == 1


def test_unconfigured_scorecard_is_explicit_not_zero_cost(tmp_path, monkeypatch):
    from scripts import run_paper_performance_scorecard as runner

    report = tmp_path / "reports"
    report.mkdir()
    p = position(date="2026-07-21", source="real_public_readonly", quarantine_status="CLEAN")
    (report / "2026-07-21_paper_position_ledger.jsonl").write_text(json.dumps(p) + "\n")
    monkeypatch.setattr("sys.argv", ["scorecard", "--date", "2026-07-21", "--output-dir", str(report)])
    assert runner.main() == 0
    payload = json.loads((report / "2026-07-21_paper_performance_scorecard.json").read_text())
    assert payload["net_friction"]["model_configuration_status"] == "UNCONFIGURED"
    assert payload["net_friction"]["complete_metrics"]["net_sample_status"] == "NO_SAMPLE"
    assert payload["net_friction"]["complete_metrics"]["net_profit_factor"] is None


def test_scorecard_preserves_distinct_assumption_versions_without_duplicates(tmp_path, monkeypatch):
    from scripts import run_paper_performance_scorecard as runner

    report = tmp_path / "reports"
    report.mkdir()
    p = position(date="2026-07-21", source="real_public_readonly", quarantine_status="CLEAN")
    (report / "2026-07-21_paper_position_ledger.jsonl").write_text(json.dumps(p) + "\n")
    first_config = tmp_path / "first.json"
    second_config = tmp_path / "second.json"
    first_config.write_text(json.dumps(assumptions(entry_fee_bps="4")))
    second_config.write_text(json.dumps(assumptions(entry_fee_bps="5")))

    def run(path):
        monkeypatch.setattr(
            "sys.argv",
            ["scorecard", "--date", "2026-07-21", "--output-dir", str(report),
             "--friction-config", str(path)],
        )
        assert runner.main() == 0
        return json.loads((report / "2026-07-21_paper_performance_scorecard.json").read_text())

    first = run(first_config)
    second = run(second_config)
    repeat = run(second_config)
    assert len(first["net_friction"]["assessments"]) == 1
    assert len(second["net_friction"]["assessments"]) == 2
    assert len(repeat["net_friction"]["assessments"]) == 2
    assert len(repeat["net_friction"]["current_assessment_ids"]) == 1
    assert repeat["global_metrics"] == first["global_metrics"]


def test_gate_net_evidence_never_promotes():
    from scripts.run_sample_collection_gate import _net_friction_gate

    blocked = _net_friction_gate({"net_friction": {"model_configuration_status": "UNCONFIGURED"}})
    assert "NET_FRICTION_MODEL_UNCONFIGURED" in blocked["net_friction_gate_blockers"]
    assert blocked["testnet_ready"] is False
    assert blocked["live_ready"] is False
    configured = _net_friction_gate({"net_friction": {
        "model_configuration_status": "CONFIGURED",
        "friction_assumptions_hash": "a" * 64,
        "p1_03_activation": {"net_friction_assumptions_hash": "a" * 64},
        "trusted_metrics": {"net_complete_closed_count": 1, "net_incomplete_closed_count": 0},
    }})
    assert configured["net_friction_gate_status"] == "EVIDENCE_AVAILABLE_REVIEW_REQUIRED"
    assert configured["automatic_promotion"] is False


def test_gate_emits_all_integrity_blockers():
    from scripts.run_sample_collection_gate import _net_friction_gate

    result = _net_friction_gate({"net_friction": {
        "model_configuration_status": "CONFIGURED",
        "integrity": {
            "symbol_mapping_invalid_count": 1,
            "notional_boundary_exceeded_count": 1,
            "funding_not_trusted_count": 1,
            "gap_evidence_incomplete_count": 1,
        },
        "trusted_metrics": {
            "net_complete_closed_count": 327,
            "net_metrics_status": "INCOMPLETE_COVERAGE",
            "outcome_selection_bias": True,
        },
    }})
    assert set(result["net_friction_gate_blockers"]) >= {
        "NET_FRICTION_SYMBOL_MAPPING_INVALID",
        "NET_FRICTION_NOTIONAL_BOUNDARY_EXCEEDED",
        "NET_FRICTION_FUNDING_NOT_TRUSTED",
        "NET_FRICTION_INCOMPLETE_COVERAGE",
        "NET_FRICTION_OUTCOME_SELECTION_BIAS",
        "NET_FRICTION_GAP_EVIDENCE_INCOMPLETE",
    }
    assert result["testnet_ready"] is result["live_ready"] is False


def test_console_public_payload_exposes_gross_net_without_assessments():
    from scripts.generate_static_console import build_public_json

    bundle = {
        "scorecard": {
            "global_metrics": {"profit_factor": 2.0, "expectancy_r": 1.0},
            "strategy_scorecards": [],
            "net_friction": {
                "friction_model_version": "net_friction_v1",
                "model_configuration_status": "CONFIGURED",
                "friction_assumptions_hash": "a" * 64,
                "gross_profit_factor": 2.0,
                "gross_expectancy_r": 1.0,
                "complete_metrics": {
                    "eligible_closed_count": 2, "complete_assessment_count": 1,
                    "partial_assessment_count": 1, "invalid_assessment_count": 0,
                    "unavailable_assessment_count": 0, "net_coverage_ratio": "0.5",
                    "net_metrics_status": "INCOMPLETE_COVERAGE",
                    "matched_subset_gross_pf": "2", "diagnostic_complete_subset_net_pf": "1.5",
                    "matched_subset_gross_expectancy": "1",
                    "diagnostic_complete_subset_net_expectancy": "0.8",
                    "excluded_by_close_reason": {"stop_loss triggered": 1},
                    "selection_bias_warning": "OUTCOME_SELECTION_BIAS_DETECTED",
                    "net_complete_closed_count": 1,
                    "net_profit_factor": "1.5",
                    "net_profit_factor_status": "FINITE",
                    "net_expectancy_r": "0.8",
                    "mean_friction_r": "-0.2",
                    "median_friction_r": "-0.2",
                    "fee_effect_r": "-0.1", "spread_effect_r": "-0.03",
                    "slippage_effect_r": "-0.05", "funding_effect_r": "-0.01",
                    "gap_effect_r": "-0.01",
                },
                "trusted_metrics": {"net_complete_closed_count": 1},
                "p1_03_activation": {"net_friction_model_version": "net_friction_v1"},
                "assessments": [{"position_id": "MUST_NOT_LEAK"}],
            },
        },
        "gate": {"sample_status": "EVALUABLE", "testnet_gate_status": "BLOCKED"},
        "counts": {"canonical": 1}, "all_canonical": [], "completion_time": "",
    }
    payload = build_public_json(bundle, "a" * 40)
    assert payload["gross_profit_factor"] == 2.0
    assert payload["net_profit_factor"] is None
    assert payload["p1_03_trusted_closed"] == 1
    assert payload["eligible_net_population"] == 2
    assert payload["net_coverage_ratio"] == "0.5"
    assert payload["net_metrics_status"] == "INCOMPLETE_COVERAGE"
    assert payload["selection_bias_warning"] == "OUTCOME_SELECTION_BIAS_DETECTED"
    assert "assessments" not in payload
    assert "MUST_NOT_LEAK" not in json.dumps(payload)


def test_wrapper_activation_is_explicit_after_gate_and_ordinary_run_does_not_activate():
    content = open("scripts/run_cloud_shadow_collection_once.sh").read()
    gate = content.index('run_step "Gate"')
    activation = content.index('run_step "Net-Friction Cohort Activation"')
    console = content.index('echo "=== Static Console ==="')
    assert gate < activation < console
    assert 'if [ "$activate_net_friction_cohort" -eq 1 ]' in content
    assert "--activate-net-friction-cohort" in content
    assert "NET_FRICTION_CONFIG" in content
    assert "validate_assumptions_for_activation" in content


def test_net_activation_cli_and_metadata_without_flag(tmp_path, monkeypatch, capsys):
    from scripts import run_paper_position_simulator as runner

    path = manifest(tmp_path)
    h = assumptions_hash(assumptions())
    monkeypatch.setattr("sys.argv", [
        "sim", "--output-dir", str(tmp_path), "--activate-net-friction-cohort",
        "--net-friction-start-at", "2026-07-21T10:00:00+00:00",
        "--net-friction-start-run-id", "run-1",
        "--net-friction-start-commit", "a" * 40,
        "--net-friction-assumptions-hash", h,
    ])
    assert runner.main() == 0
    assert "ACTIVATED" in capsys.readouterr().out
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    assert runner.main() == 0
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    monkeypatch.setattr("sys.argv", [
        "sim", "--output-dir", str(tmp_path), "--net-friction-start-at",
        "2026-07-21T10:00:00+00:00",
    ])
    assert runner.main() == 1


# P1-03A-R3A public friction evidence collector

STRATEGY_CONFIG = "config/strategies.yaml"


def evidence_context(**overrides):
    value = {
        "pipeline_run_id": "run-fixture",
        "pipeline_commit": "a" * 40,
        "report_date": "2026-07-22",
        "collected_at": "2026-07-22T01:00:30+00:00",
        "fixture_mode": "true",
    }
    value.update(overrides)
    return value


def evidence_config():
    return load_evidence_config(STRATEGY_CONFIG)


def evidence_universe():
    return resolve_active_universe(STRATEGY_CONFIG, evidence_config())


def raw_book(symbol="BTCUSDT", **overrides):
    value = {
        "symbol": symbol,
        "best_bid_price": "99",
        "best_bid_quantity": "1000",
        "best_ask_price": "101",
        "best_ask_quantity": "1000",
        "exchange_event_at": "2026-07-22T01:00:00+00:00",
        "source": "local_fixture",
    }
    value.update(overrides)
    return value


def raw_depth(symbol="BTCUSDT", **overrides):
    value = {
        "symbol": symbol,
        "bids": [["99", "100"], ["98", "100"]],
        "asks": [["101", "100"], ["102", "100"]],
        "exchange_event_at": "2026-07-22T01:00:00+00:00",
        "source": "local_fixture",
    }
    value.update(overrides)
    return value


def raw_funding(symbol="BTCUSDT", **overrides):
    value = {
        "symbol": symbol,
        "funding_event_at": "2026-07-22T00:00:00+00:00",
        "signed_funding_rate": "0.001",
        "mark_price": "100",
        "funding_interval_seconds": 28800,
        "source": "local_fixture",
        "source_event_identity": f"{symbol}:202607220000",
    }
    value.update(overrides)
    return value


def build_book(raw=None, **kwargs):
    return build_top_of_book_evidence(
        raw or raw_book(), expected_symbol=kwargs.get("symbol", "BTCUSDT"),
        context=kwargs.get("context", evidence_context()), config=evidence_config(),
        inventory_hash=evidence_universe()["strategy_inventory_hash"],
    )


def build_depth(raw=None, **kwargs):
    return build_depth_evidence(
        raw or raw_depth(), expected_symbol=kwargs.get("symbol", "BTCUSDT"),
        context=kwargs.get("context", evidence_context()), config=evidence_config(),
        inventory_hash=evidence_universe()["strategy_inventory_hash"],
    )


def build_funding(raw=None, **kwargs):
    return build_funding_evidence(
        raw or raw_funding(), expected_symbol=kwargs.get("symbol", "BTCUSDT"),
        context=kwargs.get("context", evidence_context()), config=evidence_config(),
        inventory_hash=evidence_universe()["strategy_inventory_hash"],
    )


def test_evidence_config_and_active_universe_are_governed():
    config = evidence_config()
    universe = evidence_universe()
    assert config["enabled"] is True
    assert config["evidence_version"] == EVIDENCE_VERSION
    assert config["diagnostic_notional_bands"] == [1000, 5000, 10000]
    assert universe["symbols"] == [
        "1000PEPEUSDT", "ARBUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT",
        "ETHUSDT", "SUIUSDT", "XRPUSDT",
    ]
    assert "SOLUSDT" not in universe["symbols"]
    assert len(universe["enabled_strategy_ids"]) == 2
    assert len(universe["strategy_inventory_hash"]) == 64


def test_unknown_venue_and_instrument_fail_closed(tmp_path):
    raw = yaml.safe_load(open(STRATEGY_CONFIG))
    for field, value in [("venue", "unknown"), ("market_type", "spot")]:
        changed = deepcopy(raw)
        changed["friction_evidence"][field] = value
        path = tmp_path / f"{field}.yaml"
        path.write_text(yaml.safe_dump(changed))
        with pytest.raises(ValueError, match="unsupported venue or instrument"):
            load_evidence_config(str(path))


def test_duplicate_symbols_across_enabled_strategies_are_requested_once(tmp_path):
    raw = yaml.safe_load(open(STRATEGY_CONFIG))
    raw["strategies"]["weak_short_watch"]["symbols"].append("BTCUSDT")
    path = tmp_path / "strategies.yaml"
    path.write_text(yaml.safe_dump(raw))
    config = load_evidence_config(str(path))
    universe = resolve_active_universe(str(path), config)
    assert universe["symbols"].count("BTCUSDT") == 1
    assert len(universe["symbols"]) == 8


def test_valid_book_spread_is_exact_and_stable():
    result = build_book()
    assert result["mid_price"] == "100"
    assert result["full_spread_bps"] == "200"
    assert result["one_leg_adverse_spread_bps"] == "100"
    assert result["quality_status"] == "VALID"
    assert result == json.loads(json.dumps(result))


@pytest.mark.parametrize(
    "mutation,error",
    [({"best_bid_price": "0"}, "positive"), ({"best_ask_price": "0"}, "positive"),
     ({"best_bid_price": "102"}, "CROSSED_BOOK"), ({"symbol": "ETHUSDT"}, "symbol mismatch")],
)
def test_malformed_book_fails_closed(mutation, error):
    with pytest.raises(ValueError, match=error):
        build_book(raw_book(**mutation))


def test_stale_book_is_classified_not_fabricated():
    result = build_book(context=evidence_context(collected_at="2026-07-22T02:00:00+00:00"))
    assert result["quality_status"] == "STALE"


def test_depth_buy_sell_multilevel_and_exact_boundary():
    asks = [(Decimal("100"), Decimal("5")), (Decimal("110"), Decimal("10"))]
    buy = book_impact(asks, Decimal("1050"), Decimal("100"))
    assert buy["fill_complete"] is True
    assert buy["levels_consumed"] == 2
    assert Decimal(buy["vwap_price"]) > 100
    assert Decimal(buy["adverse_impact_bps"]) > 0
    exact = book_impact(asks, Decimal("500"), Decimal("100"))
    assert exact["fill_complete"] is True
    assert exact["vwap_price"] == "100"


def test_depth_evidence_contains_bounded_estimates_not_actual_slippage():
    result = build_depth()
    assert result["quality_status"] == "VALID"
    assert result["actual_slippage_available"] is False
    assert result["diagnostic_notional_bands"] == ["1000", "5000", "10000"]
    serialized = json.dumps(result)
    assert "BOOK_IMPACT_ESTIMATE" in serialized
    assert "actual slippage" not in serialized.lower()
    assert all(Decimal(item["adverse_impact_bps"]) >= 0 for item in result["buy_book_impact_bps_by_notional"].values())
    assert all(Decimal(item["adverse_impact_bps"]) >= 0 for item in result["sell_book_impact_bps_by_notional"].values())


def test_insufficient_depth_and_bad_levels_fail_closed():
    result = build_depth(raw_depth(bids=[["99", "1"]], asks=[["101", "1"]]))
    assert result["quality_status"] == "INSUFFICIENT_DEPTH"
    with pytest.raises(ValueError, match="positive"):
        build_depth(raw_depth(bids=[["99", "0"]]))


def test_duplicate_depth_prices_are_normalized_deterministically():
    result = build_depth(raw_depth(
        bids=[["99", "50"], ["99", "50"]],
        asks=[["101", "50"], ["101", "50"]],
    ))
    assert result["bid_levels"][0] == ["99", "100"]
    assert result["ask_levels"][0] == ["101", "100"]


def test_notional_bands_change_depth_payload_hash():
    first = build_depth()
    config = evidence_config()
    config["diagnostic_notional_bands"] = [1000]
    second = build_depth_evidence(
        raw_depth(), expected_symbol="BTCUSDT", context=evidence_context(), config=config,
        inventory_hash=evidence_universe()["strategy_inventory_hash"],
    )
    assert first["payload_hash"] != second["payload_hash"]


def test_funding_signed_rate_identity_and_conflict(tmp_path):
    store = EvidenceStore(str(tmp_path / "evidence.jsonl"))
    positive = build_funding()
    assert positive["signed_funding_rate"] == "0.001"
    assert store.append(positive).status == "APPENDED"
    before = (tmp_path / "evidence.jsonl").read_bytes()
    assert store.append(deepcopy(positive)).status == "EXACT_DUPLICATE_NO_WRITE"
    replay = build_funding(
        raw_funding(funding_interval_seconds=28799),
        context=evidence_context(
            collected_at="2026-07-22T02:00:00+00:00",
            pipeline_run_id="replay-run",
        ),
    )
    assert replay["evidence_id"] == positive["evidence_id"]
    assert replay["payload_hash"] != positive["payload_hash"]
    assert store.append(replay).status == "FUNDING_SEMANTIC_REPLAY_NO_WRITE"
    negative = build_funding(raw_funding(signed_funding_rate="-0.001"))
    assert negative["evidence_id"] == positive["evidence_id"]
    assert store.append(negative).status == "CONFLICT_REJECTED"
    changed_source_identity = build_funding(raw_funding(source_event_identity="BTCUSDT:different"))
    assert changed_source_identity["evidence_id"] == positive["evidence_id"]
    assert store.append(changed_source_identity).status == "CONFLICT_REJECTED"
    changed_mark = build_funding(raw_funding(mark_price="101"))
    assert store.append(changed_mark).status == "CONFLICT_REJECTED"
    assert (tmp_path / "evidence.jsonl").read_bytes() == before


def test_funding_new_event_appends_then_provenance_repeat_is_semantic_no_write(tmp_path):
    store = EvidenceStore(str(tmp_path / "evidence.jsonl"))
    event = build_funding(raw_funding(funding_event_at="2026-07-22T08:00:00+00:00"))
    assert store.append(event).status == "APPENDED"
    before = (tmp_path / "evidence.jsonl").read_bytes()
    replay = build_funding(
        raw_funding(funding_event_at="2026-07-22T08:00:00+00:00"),
        context=evidence_context(
            collected_at="2026-07-22T09:00:00+00:00",
            pipeline_run_id="later-run", pipeline_commit="b" * 40,
            report_date="2026-07-23",
        ),
    )
    assert store.append(replay).status == "FUNDING_SEMANTIC_REPLAY_NO_WRITE"
    later = build_funding(raw_funding(funding_event_at="2026-07-22T16:00:00+00:00"))
    assert later["evidence_id"] != event["evidence_id"]
    assert store.append(later).status == "APPENDED"
    other_symbol = build_funding(
        raw_funding(symbol="ETHUSDT", funding_event_at="2026-07-22T08:00:00+00:00"),
        symbol="ETHUSDT",
    )
    assert other_symbol["evidence_id"] != event["evidence_id"]
    assert store.append(other_symbol).status == "APPENDED"
    assert (tmp_path / "evidence.jsonl").read_bytes().startswith(before)


def test_evidence_store_identity_hash_append_only_and_restart(tmp_path):
    path = tmp_path / "evidence.jsonl"
    store = EvidenceStore(str(path))
    record = build_book()
    assert store.append(record).status == "APPENDED"
    prefix = path.read_bytes()
    changed_collection = build_book(context=evidence_context(
        collected_at="2026-07-22T01:01:00+00:00", pipeline_run_id="retry",
    ))
    assert changed_collection["evidence_id"] == record["evidence_id"]
    assert changed_collection["payload_hash"] == record["payload_hash"]
    assert EvidenceStore(str(path)).append(changed_collection).status == "EXACT_DUPLICATE_NO_WRITE"
    assert path.read_bytes() == prefix
    second = build_book(raw_book(exchange_event_at="2026-07-22T01:01:00+00:00"))
    assert store.append(second).status == "APPENDED"
    assert path.read_bytes().startswith(prefix)


def test_malformed_store_record_rejected(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"bad":true}\n')
    with pytest.raises(ValueError, match="malformed evidence record"):
        EvidenceStore(str(path)).read_all()


def test_tampered_evidence_store_record_is_rejected(tmp_path):
    path = tmp_path / "evidence.jsonl"
    path.write_text(json.dumps({**build_book(), "best_ask_price": "999"}) + "\n")
    with pytest.raises(ValueError, match="payload hash mismatch"):
        EvidenceStore(str(path)).read_all()


@pytest.mark.parametrize(
    "side,rate,sign",
    [("LONG", "0.001", -1), ("SHORT", "0.001", 1),
     ("LONG", "-0.001", 1), ("SHORT", "-0.001", -1)],
)
def test_position_funding_attribution_direction_and_boundaries(side, rate, sign):
    entry = build_funding(raw_funding(
        funding_event_at="2026-07-21T00:00:00+00:00", signed_funding_rate=rate,
    ))
    inside = build_funding(raw_funding(
        funding_event_at="2026-07-21T04:00:00+00:00", signed_funding_rate=rate,
    ))
    exit_event = build_funding(raw_funding(
        funding_event_at="2026-07-21T09:00:00+00:00", signed_funding_rate=rate,
    ))
    wrong = build_funding(raw_funding(
        symbol="ETHUSDT", funding_event_at="2026-07-21T04:00:00+00:00",
        signed_funding_rate=rate,
    ), symbol="ETHUSDT")
    result = attribute_position_funding(
        position(side=side), [entry, inside, exit_event, wrong],
        query_succeeded=True, expected_windows_resolved=True,
    )
    assert result["event_count"] == 2
    assert Decimal(result["funding_effect_quote"]).compare(Decimal("0")) == Decimal(sign)
    assert result["attribution_version"] == ATTRIBUTION_VERSION
    assert result["funding_completeness"] == "COMPLETE"


def test_zero_funding_events_require_authoritative_continuity():
    partial = attribute_position_funding(
        position(), [], query_succeeded=True, expected_windows_resolved=False,
    )
    complete = attribute_position_funding(
        position(), [], query_succeeded=True, expected_windows_resolved=True,
    )
    assert partial["funding_completeness"] == "PARTIAL"
    assert partial["zero_events_proven"] is False
    assert complete["zero_events_proven"] is True


def test_position_funding_attribution_is_deterministic_evidence(tmp_path):
    event = build_funding(raw_funding(funding_event_at="2026-07-21T04:00:00+00:00"))
    record = build_position_funding_attribution_evidence(
        position(), [event], query_succeeded=True, expected_windows_resolved=True,
        context=evidence_context(), config=evidence_config(),
        inventory_hash=evidence_universe()["strategy_inventory_hash"],
    )
    assert record["evidence_type"] == "POSITION_FUNDING_ATTRIBUTION"
    assert record["attribution_version"] == ATTRIBUTION_VERSION
    store = EvidenceStore(str(tmp_path / "evidence.jsonl"))
    assert store.append(record).status == "APPENDED"
    assert store.append(deepcopy(record)).status == "EXACT_DUPLICATE_NO_WRITE"


def test_zero_event_public_query_is_recorded_partial_not_complete():
    result = build_funding_coverage_evidence(
        symbol="BTCUSDT", events=[], context=evidence_context(), config=evidence_config(),
        inventory_hash=evidence_universe()["strategy_inventory_hash"],
    )
    assert result["query_succeeded"] is True
    assert result["returned_event_count"] == 0
    assert result["expected_windows_resolved"] is False
    assert result["zero_events_proven"] is False
    assert result["quality_status"] == "PARTIAL"


def _stop(side, gap, *, closed_at="2026-07-22T01:00:00+00:00", valid=True, strategy="s"):
    stop = "95" if side == "LONG" else "105"
    value = position(
        position_id=f"{side}-{gap}-{closed_at}-{strategy}", strategy_id=strategy,
        side=side, status="STOP_LOSS_HIT", exit_reason="stop_loss triggered",
        closed_at=closed_at, stop_loss=stop, exit_price=stop,
        gap_execution_reference_price=gap, exit_trigger_bar_open=gap,
        exit_trigger_bar_close_time=closed_at, nominal_stop_price=stop,
        gap_execution_evidence_version="stop_trigger_bar_open_v1",
    )
    if not valid:
        for field in (
            "gap_execution_reference_price", "exit_trigger_bar_open",
            "exit_trigger_bar_close_time", "nominal_stop_price", "gap_execution_evidence_version",
        ):
            value.pop(field, None)
    return value


def test_stop_readiness_separates_legacy_and_classifies_direction_gap():
    positions = [
        _stop("LONG", "95"), _stop("LONG", "90"),
        _stop("SHORT", "105"), _stop("SHORT", "110"),
        _stop("LONG", "90", closed_at="2026-07-19T01:00:00+00:00", valid=False),
    ]
    result = stop_evidence_summary(positions, "2026-07-22T00:00:00+00:00")
    assert result["prospective_stop_count"] == 4
    assert result["prospective_stop_with_gap_evidence"] == 4
    assert result["prospective_gap_coverage_ratio"] == "1"
    assert result["long_stop_count"] == result["short_stop_count"] == 2
    assert result["normal_stop_count"] == result["gap_through_stop_count"] == 2


def test_missing_prospective_gap_prevents_complete_coverage():
    result = stop_evidence_summary([
        _stop("LONG", "90"), _stop("SHORT", "110", valid=False),
    ], "2026-07-22T00:00:00+00:00")
    assert result["prospective_gap_coverage_ratio"] == "0.5"


class FixtureEvidenceAdapter:
    def __init__(self, conflict=False):
        self.requested = []
        self.conflict = conflict

    def get_top_of_book(self, symbol):
        self.requested.append(("book", symbol))
        ask = "102" if self.conflict and symbol == "BTCUSDT" else "101"
        return raw_book(symbol, best_ask_price=ask)

    def get_depth(self, symbol, limit):
        self.requested.append(("depth", symbol))
        return raw_depth(symbol)

    def get_funding_events(self, symbol, lookback):
        self.requested.append(("funding", symbol))
        return [raw_funding(symbol)]


class OneSymbolFailureAdapter(FixtureEvidenceAdapter):
    def get_top_of_book(self, symbol):
        if symbol == "BTCUSDT":
            raise ValueError("fixture source failure")
        return super().get_top_of_book(symbol)


class FundingRateConflictAdapter(FixtureEvidenceAdapter):
    def get_funding_events(self, symbol, lookback):
        self.requested.append(("funding", symbol))
        return [raw_funding(symbol, signed_funding_rate="0.002")]


def test_controlled_eight_symbol_cycle_repeat_and_conflict(tmp_path):
    first_adapter = FixtureEvidenceAdapter()
    first = collect_evidence_cycle(
        strategy_config_path=STRATEGY_CONFIG, output_dir=str(tmp_path),
        adapter=first_adapter, context=evidence_context(),
    )
    assert first["status"] == "PASS"
    assert first["active_symbol_count"] == 8
    assert first["appended"] == 32
    assert first["duplicate_symbol_requests"] == 0
    assert first["authenticated_calls"] == first["orders"] == 0
    assert len({symbol for kind, symbol in first_adapter.requested if kind == "book"}) == 8
    path = tmp_path / "friction_evidence.jsonl"
    before = path.read_bytes()
    repeat = collect_evidence_cycle(
        strategy_config_path=STRATEGY_CONFIG, output_dir=str(tmp_path),
        adapter=FixtureEvidenceAdapter(), context=evidence_context(pipeline_run_id="retry"),
    )
    assert repeat["appended"] == 0
    assert repeat["duplicates"] == 32
    assert repeat["funding_exact_duplicate_no_writes"] == 0
    assert repeat["funding_semantic_replay_no_writes"] == 8
    assert repeat["funding_true_conflicts"] == 0
    assert path.read_bytes() == before
    conflict = collect_evidence_cycle(
        strategy_config_path=STRATEGY_CONFIG, output_dir=str(tmp_path),
        adapter=FixtureEvidenceAdapter(conflict=True), context=evidence_context(pipeline_run_id="conflict"),
    )
    assert conflict["status"] == "CONFLICT"
    assert conflict["conflicts"] == 1
    assert path.read_bytes() == before


def test_funding_true_conflict_is_counted_and_store_is_unchanged(tmp_path):
    first = collect_evidence_cycle(
        strategy_config_path=STRATEGY_CONFIG, output_dir=str(tmp_path),
        adapter=FixtureEvidenceAdapter(), context=evidence_context(),
    )
    assert first["new_funding_events"] == 8
    path = tmp_path / "friction_evidence.jsonl"
    before = path.read_bytes()
    conflict = collect_evidence_cycle(
        strategy_config_path=STRATEGY_CONFIG, output_dir=str(tmp_path),
        adapter=FundingRateConflictAdapter(), context=evidence_context(),
    )
    assert conflict["status"] == "CONFLICT"
    assert conflict["funding_true_conflicts"] == 8
    assert conflict["funding_semantic_replay_no_writes"] == 0
    assert path.read_bytes() == before


def test_observation_only_source_failure_is_audited_and_isolated(tmp_path):
    result = collect_evidence_cycle(
        strategy_config_path=STRATEGY_CONFIG, output_dir=str(tmp_path),
        adapter=OneSymbolFailureAdapter(), context=evidence_context(),
    )
    assert result["status"] == "PASS_WITH_SOURCE_ERRORS"
    assert result["source_errors"] == 1
    rows = EvidenceStore(str(tmp_path / "friction_evidence.jsonl")).read_all()
    failures = [row for row in rows if row["evidence_type"] == "SOURCE_QUALITY_FAILURE"]
    assert len(failures) == 1
    assert failures[0]["symbol"] == "BTCUSDT"
    assert failures[0]["quality_status"] == "SOURCE_ERROR"
    assert any(row["symbol"] == "ETHUSDT" and row["evidence_type"] == "TOP_OF_BOOK" for row in rows)


def _readiness_book(symbol, observed_at, valid=True):
    return {
        "symbol": symbol, "evidence_type": "TOP_OF_BOOK",
        "observed_at": observed_at, "quality_status": "VALID" if valid else "STALE",
        "one_leg_adverse_spread_bps": "1",
    }


def _readiness_depth(symbol, observed_at):
    impacts = {str(band): {"adverse_impact_bps": "1"} for band in (1000, 5000, 10000)}
    return {
        "symbol": symbol, "evidence_type": "DEPTH_BOOK_IMPACT_ESTIMATE",
        "observed_at": observed_at, "quality_status": "VALID",
        "buy_book_impact_bps_by_notional": impacts,
        "sell_book_impact_bps_by_notional": impacts,
    }


def test_readiness_immature_and_mature_remain_human_governed():
    universe = evidence_universe()
    config = evidence_config()
    immature = build_readiness_report(
        [], universe=universe, positions=[], prospective_start_at="2026-07-01T00:00:00+00:00",
        config=config, funding_continuity={},
    )
    assert immature["status"] == "MORE_DATA"
    rows = []
    for symbol in universe["symbols"]:
        for day_index in range(14):
            for sample in range(18):
                observed = f"2026-07-{day_index + 1:02d}T{sample:02d}:00:00+00:00"
                rows.extend([_readiness_book(symbol, observed), _readiness_depth(symbol, observed)])
    stops = [
        _stop("LONG" if index % 2 == 0 else "SHORT", "90" if index % 2 == 0 else "110",
              closed_at=f"2026-07-20T{index % 24:02d}:00:00+00:00",
              strategy="macd_rebound_watch" if index < 15 else "weak_short_watch")
        for index in range(30)
    ]
    mature = build_readiness_report(
        rows, universe=universe, positions=stops,
        prospective_start_at="2026-07-01T00:00:00+00:00", config=config,
        funding_continuity={symbol: True for symbol in universe["symbols"]},
    )
    assert mature["status"] == "READY_FOR_HUMAN_REVIEW"
    assert mature["assumptions_approved"] is False
    assert mature["p1_03_cohort_activated"] is False
    assert mature["testnet_enabled"] is mature["live_enabled"] is False
    assert mature["actual_account_fee_tier"] == "UNVERIFIED"


def test_readiness_each_target_fails_closed():
    universe = evidence_universe()
    config = evidence_config()
    base = build_readiness_report(
        [_readiness_book(symbol, "2026-07-01T00:00:00+00:00") for symbol in universe["symbols"]],
        universe=universe, positions=[_stop("LONG", "90")],
        prospective_start_at="2026-07-01T00:00:00+00:00", config=config,
        funding_continuity={symbol: False for symbol in universe["symbols"]},
    )
    assert base["status"] == "MORE_DATA"
    assert all(row["symbol_readiness"] == "MORE_DATA" for row in base["per_symbol"].values())


def test_readiness_success_ratio_counts_source_failures():
    universe = evidence_universe()
    rows = [_readiness_book("BTCUSDT", "2026-07-01T00:00:00+00:00")]
    failure = {
        "symbol": "BTCUSDT", "evidence_type": "SOURCE_QUALITY_FAILURE",
        "failed_evidence_type": "TOP_OF_BOOK", "observed_at": "2026-07-01T01:00:00+00:00",
        "quality_status": "SOURCE_ERROR",
    }
    rows.append(failure)
    report = build_readiness_report(
        rows, universe=universe, positions=[],
        prospective_start_at="2026-07-01T00:00:00+00:00",
        config=evidence_config(), funding_continuity={},
    )
    btc = report["per_symbol"]["BTCUSDT"]
    assert btc["valid_book_snapshot_count"] == 1
    assert btc["invalid_book_snapshot_count"] == 1
    assert btc["snapshot_success_ratio"] == "0.5"


def test_readiness_report_is_machine_readable_and_explicit(tmp_path):
    report = build_readiness_report(
        [], universe=evidence_universe(), positions=[],
        prospective_start_at="2026-07-01T00:00:00+00:00",
        config=evidence_config(), funding_continuity={},
    )
    path = tmp_path / "friction_evidence_readiness.json"
    assert write_readiness_report(report, str(path)) == str(path)
    loaded = json.loads(path.read_text())
    assert loaded["status"] == "MORE_DATA"
    assert loaded["actual_account_fee_tier"] == "UNVERIFIED"
    assert loaded["human_approval_required"] is True


def test_wrapper_evidence_path_is_explicit_observation_only():
    content = open("scripts/run_cloud_shadow_collection_once.sh").read()
    assert "--collect-friction-evidence" in content
    assert "--check-config-enabled" in content
    assert 'if [ "$FRICTION_EVIDENCE_CONFIG_ENABLED" -eq 1 ]' in content
    collector_block = content[content.index('if [ "$FRICTION_EVIDENCE_CONFIG_ENABLED" -eq 1 ]'):]
    assert "python3 -m core.paper_trading.friction_evidence" in collector_block
    assert "FRICTION_EVIDENCE_ENABLEMENT_SOURCE:" in content
    assert "Public friction evidence hard failure; aborting pipeline" in content
    assert "core.paper_trading.friction_evidence" in content
    assert "activate-net-friction-cohort" in content  # remains a separate explicit path


def _governed_wrapper_fixture(tmp_path, *, config_enabled, collector_result="PASS"):
    project = tmp_path / "project"
    fakebin = project / "fakebin"
    (project / ".venv" / "bin").mkdir(parents=True)
    (project / "logs" / "cloud_shadow").mkdir(parents=True)
    fakebin.mkdir()
    call_log = tmp_path / "calls.log"
    (project / ".venv" / "bin" / "activate").write_text(
        f'export PATH="{fakebin}:$PATH"\n'
    )
    fake_python = fakebin / "python3"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "if [[ \"$*\" == *--check-config-enabled* ]]; then\n"
        "  if [ \"$CONFIG_ENABLED\" = 1 ]; then echo ENABLED; exit 0; fi\n"
        "  echo DISABLED; exit 3\n"
        "elif [[ \"$*\" == *build_pipeline_context* ]]; then\n"
        "  echo 'RUN-GOVERNED 2026-07-22T01:00:30+00:00 2026-07-22'\n"
        "elif [[ \"$*\" == *core.paper_trading.friction_evidence* ]]; then\n"
        "  if [ \"$COLLECTOR_RESULT\" = CONFLICT ]; then\n"
        "    echo '{\"status\": \"CONFLICT\", \"funding_true_conflicts\": 1}'\n"
        "    exit 1\n"
        "  fi\n"
        "  echo '{\"status\": \"PASS\", \"active_symbol_count\": 8, \"appended\": 32, \"funding_semantic_replay_no_writes\": 16, \"duplicate_symbol_requests\": 0, \"authenticated_calls\": 0, \"orders\": 0}'\n"
        "fi\n"
    )
    fake_python.chmod(0o755)
    fake_git = fakebin / "git"
    fake_git.write_text("#!/usr/bin/env bash\necho " + "a" * 40 + "\n")
    fake_git.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "PROJECT_DIR": str(project), "CALL_LOG": str(call_log),
        "CONFIG_ENABLED": "1" if config_enabled else "0",
        "COLLECTOR_RESULT": collector_result,
        "PATH": f"{fakebin}:{env['PATH']}",
    })
    return call_log, env


@pytest.mark.parametrize(
    ("config_enabled", "cli_requested", "expected_result", "expected_source", "cycles"),
    [
        (False, False, "DISABLED", "DISABLED_BY_TRACKED_CONFIG", 0),
        (False, True, "DISABLED", "DISABLED_BY_TRACKED_CONFIG", 0),
        (True, False, "COLLECTED", "TRACKED_CONFIG", 1),
        (True, True, "COLLECTED", "TRACKED_CONFIG", 1),
    ],
)
def test_wrapper_tracked_config_is_single_master_switch(
    tmp_path, config_enabled, cli_requested, expected_result, expected_source, cycles,
):
    call_log, env = _governed_wrapper_fixture(tmp_path, config_enabled=config_enabled)
    command = ["bash", "scripts/run_cloud_shadow_collection_once.sh"]
    if cli_requested:
        command.append("--collect-friction-evidence")
    result = subprocess.run(command, cwd=".", env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout
    assert f"FRICTION_EVIDENCE_CONFIG_ENABLED:{'YES' if config_enabled else 'NO'}" in output
    assert f"FRICTION_EVIDENCE_CLI_REQUESTED:{'YES' if cli_requested else 'NO'}" in output
    assert f"FRICTION_EVIDENCE_EXECUTION_REQUESTED:{'YES' if config_enabled else 'NO'}" in output
    assert f"FRICTION_EVIDENCE_ENABLEMENT_SOURCE:{expected_source}" in output
    assert f"FRICTION_EVIDENCE_RESULT:{expected_result}" in output
    calls = call_log.read_text().splitlines()
    collection_calls = [
        line for line in calls
        if "core.paper_trading.friction_evidence" in line and "--allow-public-http" in line
    ]
    assert len(collection_calls) == cycles
    assert not any("--activate-net-friction-cohort" in line for line in calls)
    assert not any("--net-friction-config" in line for line in calls)
    assert "cc9bc6bbb9fd4a7b81f438391e35ae91f7d64e2767d1e8b732451dab923befc3" not in output
    assert "48edb9dcacbb032d69bdc16ffffd91b786b399c8ce8a88199ccbe676d4653a91" not in output
    if not config_enabled and cli_requested:
        assert "friction_evidence_decision=DISABLED_BY_TRACKED_CONFIG" in output


def test_wrapper_propagates_true_evidence_conflict_nonzero(tmp_path):
    call_log, env = _governed_wrapper_fixture(
        tmp_path, config_enabled=True, collector_result="CONFLICT",
    )
    result = subprocess.run(
        ["bash", "scripts/run_cloud_shadow_collection_once.sh"],
        cwd=".", env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "FRICTION_EVIDENCE_RESULT:FAIL" in result.stdout
    assert "Public friction evidence hard failure; aborting pipeline" in result.stdout
    calls = call_log.read_text().splitlines()
    collector_index = next(i for i, line in enumerate(calls) if "--allow-public-http" in line and "friction_evidence" in line)
    assert not any("run_paper_performance_scorecard.py" in line for line in calls[collector_index + 1:])
    assert not (tmp_path / "project" / "reports").exists()


@pytest.mark.parametrize("bad_enabled", ["true", 1, None])
def test_evidence_config_enabled_must_be_boolean(tmp_path, bad_enabled):
    raw = yaml.safe_load(open(STRATEGY_CONFIG))
    raw["friction_evidence"]["enabled"] = bad_enabled
    path = tmp_path / "strategies.yaml"
    path.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError, match="enabled must be boolean"):
        load_evidence_config(str(path))


def _boundary_records(*, collected_at="2026-07-22T15:58:23+00:00"):
    context = evidence_context(collected_at=collected_at)
    book = build_book(context=context)
    funding = build_funding(
        raw=raw_funding(funding_event_at="2026-07-21T16:00:00.002+00:00"),
        context=context,
    )
    return [book, funding]


def test_boundary_uses_collected_at_not_historical_funding_observed_at():
    boundary = derive_prospective_boundary(_boundary_records())
    assert boundary["prospective_stop_cohort_start_at"] == "2026-07-22T15:58:23+00:00"
    assert boundary["earliest_evidence_observed_at"] == "2026-07-21T16:00:00.002+00:00"
    assert boundary["earliest_evidence_collected_at"] == "2026-07-22T15:58:23+00:00"
    assert boundary["prospective_boundary_source"] == PROSPECTIVE_BOUNDARY_SOURCE
    assert boundary["prospective_boundary_version"] == PROSPECTIVE_BOUNDARY_VERSION


def test_boundary_is_immutable_across_later_appends_and_old_event_times():
    initial = derive_prospective_boundary(_boundary_records())
    later = _boundary_records(collected_at="2026-07-23T00:58:23+00:00")
    later.append(build_depth(context=evidence_context(collected_at="2026-07-23T00:58:23+00:00")))
    later[1]["observed_at"] = "2020-01-01T00:00:00.000+00:00"
    later[1]["exchange_event_at"] = "2020-01-01T00:00:00.000+00:00"
    later[1]["evidence_id"] = evidence_id(later[1])
    later[1]["payload_hash"] = payload_hash(later[1])
    repeated = derive_prospective_boundary(_boundary_records() + later, initial)
    assert repeated["prospective_stop_cohort_start_at"] == initial["prospective_stop_cohort_start_at"]


def test_existing_boundary_conflict_fails_closed():
    existing = {
        "prospective_stop_cohort_start_at": "2026-07-22T16:00:00+00:00",
        "prospective_boundary_source": PROSPECTIVE_BOUNDARY_SOURCE,
        "prospective_boundary_version": PROSPECTIVE_BOUNDARY_VERSION,
    }
    with pytest.raises(ValueError, match="boundary conflicts"):
        derive_prospective_boundary(_boundary_records(), existing)


@pytest.mark.parametrize("bad_value", [None, "not-a-time"])
def test_missing_or_malformed_collected_at_never_falls_back(bad_value):
    row = _boundary_records()[1]
    if bad_value is None:
        row.pop("collected_at")
    else:
        row["collected_at"] = bad_value
    row["payload_hash"] = payload_hash(row)
    boundary = derive_prospective_boundary([row])
    assert boundary["prospective_boundary_status"] == "UNAVAILABLE"
    assert boundary["prospective_stop_cohort_start_at"] is None
    assert boundary["malformed_collected_at_records"] == 1


def test_boundary_does_not_require_diagnostic_observed_at_to_be_parseable():
    row = _boundary_records()[1]
    row["observed_at"] = "not-a-timestamp"
    row["evidence_id"] = evidence_id(row)
    row["payload_hash"] = payload_hash(row)

    boundary = derive_prospective_boundary([row])

    assert boundary["prospective_boundary_status"] == "READY"
    assert boundary["prospective_stop_cohort_start_at"] == "2026-07-22T15:58:23+00:00"
    assert boundary["earliest_evidence_observed_at"] is None
    assert boundary["malformed_collected_at_records"] == 0


def test_stop_boundary_is_inclusive_and_empty_sample_is_explicit():
    boundary = "2026-07-22T15:58:23+00:00"
    pre = _stop("LONG", "90", closed_at="2026-07-22T15:58:22+00:00")
    equal = _stop("SHORT", "110", closed_at=boundary)
    empty = stop_evidence_summary([pre], boundary, "2026-07-21T16:00:00+00:00")
    assert empty["historical_stops_before_prospective_boundary"] == 1
    assert empty["prospective_stop_count"] == 0
    assert empty["prospective_stop_missing_gap_evidence"] == 0
    assert empty["prospective_gap_coverage_status"] == "NO_SAMPLE"
    included = stop_evidence_summary([pre, equal], boundary, "2026-07-21T16:00:00+00:00")
    assert included["prospective_stop_count"] == 1
    assert included["prospective_stop_with_gap_evidence"] == 1
    assert included["prospective_gap_coverage_status"] == "COMPLETE"


def test_post_boundary_missing_gap_is_in_denominator():
    stop = _stop("LONG", "90", closed_at="2026-07-22T16:00:00+00:00", valid=False)
    result = stop_evidence_summary([stop], "2026-07-22T15:58:23+00:00")
    assert result["prospective_stop_count"] == 1
    assert result["prospective_stop_with_gap_evidence"] == 0
    assert result["prospective_stop_missing_gap_evidence"] == 1
    assert result["prospective_gap_coverage_status"] == "INCOMPLETE"


def test_readiness_only_regeneration_preserves_evidence_bytes(tmp_path):
    collect_evidence_cycle(
        strategy_config_path=STRATEGY_CONFIG, output_dir=str(tmp_path),
        adapter=FixtureEvidenceAdapter(), context=evidence_context(),
    )
    store_path = tmp_path / "friction_evidence.jsonl"
    before = store_path.read_bytes()
    historical = _stop("LONG", "90", closed_at="2026-07-22T01:00:00+00:00")
    (tmp_path / "2026-07-22_paper_position_ledger.jsonl").write_text(json.dumps(historical) + "\n")
    report = regenerate_readiness(STRATEGY_CONFIG, str(tmp_path))
    assert store_path.read_bytes() == before
    assert report["prospective_stop_cohort_start_at"] == "2026-07-22T01:00:30+00:00"
    assert report["prospective_boundary_source"] == PROSPECTIVE_BOUNDARY_SOURCE
    assert report["prospective_stops"]["prospective_stop_count"] == 0
    assert report["prospective_stops"]["prospective_stop_missing_gap_evidence"] == 0
    assert report["prospective_stops"]["prospective_gap_coverage_status"] == "NO_SAMPLE"
    assert report["status"] == "MORE_DATA"
    repeated = regenerate_readiness(STRATEGY_CONFIG, str(tmp_path))
    assert repeated["prospective_stop_cohort_start_at"] == report["prospective_stop_cohort_start_at"]
    assert store_path.read_bytes() == before
