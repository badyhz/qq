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
)


def assumptions(**overrides):
    value = {
        "friction_model_version": "net_friction_v1",
        "instrument_type": "linear_spot",
        "venue": "fixture_exchange",
        "quote_currency": "USDT",
        "entry_fee_bps": "4",
        "exit_fee_bps": "4",
        "entry_spread_bps": "1",
        "exit_spread_bps": "1",
        "entry_slippage_bps": "2",
        "exit_slippage_bps": "2",
        "spread_input_semantics": "ONE_LEG_ADVERSE_BPS",
        "slippage_source": "CONFIGURED_ESTIMATE",
        "funding_mode": "NOT_APPLICABLE",
        "gap_execution_mode": "OBSERVED_FIRST_EXECUTABLE",
    }
    value.update(overrides)
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
        "entry_price": "100",
        "exit_price": "110",
        "stop_loss": "95",
        "position_size_preview": "2",
        "opened_at": "2026-07-21T00:00:00+00:00",
        "closed_at": "2026-07-21T09:00:00+00:00",
        "exit_reason": "take_profit triggered",
        "realized_pnl": "20",
        "r_multiple": "2",
        "signal_bar_contract_version": "closed_bar_v1",
    }
    value.update(overrides)
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
        "at": "2026-07-21T08:00:00+00:00", "rate": rate, "mark_price": "105",
    }])
    config = assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS")
    result = assess_position_friction(p, config)
    assert D(result, "funding_effect_quote").compare(Decimal("0")) == Decimal(expected_sign)


def test_multiple_funding_events_and_boundary_entry_excluded_exit_included():
    p = position(funding_events=[
        {"at": "2026-07-21T00:00:00+00:00", "rate": "0.001", "mark_price": "100"},
        {"at": "2026-07-21T04:00:00+00:00", "rate": "0.001", "mark_price": "100"},
        {"at": "2026-07-21T09:00:00+00:00", "rate": "0.001", "mark_price": "100"},
        {"at": "2026-07-21T10:00:00+00:00", "rate": "0.001", "mark_price": "100"},
    ])
    result = assess_position_friction(
        p, assumptions(instrument_type="linear_perpetual", funding_mode="OBSERVED_EVENTS"),
    )
    assert D(result, "funding_effect_quote") == Decimal("-0.4")


def test_configured_funding_intervals_count_once():
    config = assumptions(
        instrument_type="linear_perpetual",
        funding_mode="CONFIGURED_RATE_PER_INTERVAL",
        funding_rate_per_interval="0.001",
        funding_interval_seconds=14400,
        funding_first_event_at="2026-07-21T00:00:00+00:00",
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
    del config["entry_fee_bps"]
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
    assert Decimal(metrics["net_expectancy_r"]) == expected
    assert metrics["net_complete_closed_count"] == 2
    assert metrics["net_incomplete_closed_count"] == 1


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
    assert p["realized_pnl"] == "20"
    assert p["r_multiple"] == "2"


def test_calculation_anchor_is_deterministic_closed_at():
    result = assess_position_friction(position(), assumptions())
    assert result["friction_calculated_at"] == position()["closed_at"]
    assert result["friction_model_version"] == FRICTION_MODEL_VERSION
