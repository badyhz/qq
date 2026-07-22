from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from decimal import Decimal

import pytest

from core.paper_trading.net_friction import (
    FRICTION_MODEL_VERSION,
    activate_net_friction_trusted_cohort,
    aggregate_net_metrics,
    assess_position_friction,
    assumptions_hash,
    is_p1_03_trusted,
    validate_assumptions_for_activation,
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
