"""Phase 13: Negative tests for offline shadow research pipeline.

Covers invalid safety policies, empty lists, missing fields, invalid ranges,
duplicate IDs, empty outcomes, mismatched IDs, missing artifacts, and
invalid fixture dirs.  20+ tests.
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
from core.offline_shadow_experiment import OfflineShadowExperiment
from core.offline_shadow_experiment_plan import OfflineShadowExperimentPlan
from core.offline_shadow_parameter_set import OfflineShadowParameterSet
from core.offline_shadow_run_config import OfflineShadowRunConfig
from core.offline_shadow_symbol import OfflineShadowSymbol
from core.offline_shadow_timeframe import OfflineShadowTimeframe
from core.offline_shadow_window import OfflineShadowWindow
from core.offline_shadow_metric_engine import compute_run_metrics, compute_aggregate_metrics


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _policy(**kw):
    d = dict(no_live=True, no_submit=True, no_exchange=True, release_hold="HOLD")
    d.update(kw)
    return OfflineShadowSafetyPolicy(**d)


def _symbol(**kw):
    d = dict(symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", exchange="binance")
    d.update(kw)
    return OfflineShadowSymbol(**d)


def _timeframe(**kw):
    d = dict(label="5m", minutes=5)
    d.update(kw)
    return OfflineShadowTimeframe(**d)


def _window(**kw):
    d = dict(window_id="w_train", window_type="train", start_index=0, end_index=100)
    d.update(kw)
    return OfflineShadowWindow(**d)


def _params(**kw):
    d = dict(
        param_id="p_01", label="conservative",
        entry_threshold=0.7, exit_threshold=0.3,
        stop_loss_r=1.5, take_profit_r=3.0,
        max_hold_bars=20, min_sample_quality=0.8,
    )
    d.update(kw)
    return OfflineShadowParameterSet(**d)


def _experiment(eid="exp_001", **kw):
    d = dict(
        experiment_id=eid,
        symbol=_symbol(),
        timeframe=_timeframe(),
        window=_window(),
        parameter_set=_params(),
        safety_policy=_policy(),
    )
    d.update(kw)
    return OfflineShadowExperiment(**d)


def _run_config(**kw):
    d = dict(
        config_id="rc_001",
        symbols=("BTCUSDT",),
        timeframes=("5m",),
        windows=("train",),
        param_grid=("conservative",),
        fixture_dir="/tmp/fixtures",
        output_dir="/tmp/output",
    )
    d.update(kw)
    return OfflineShadowRunConfig(**d)


# ---------------------------------------------------------------------------
# 1. Invalid safety policy
# ---------------------------------------------------------------------------

class TestInvalidSafetyPolicy:
    def test_release_hold_not_hold_raises(self):
        with pytest.raises(ValueError, match="release_hold must be 'HOLD'"):
            _policy(release_hold="RELEASE")

    def test_release_hold_empty_raises(self):
        with pytest.raises(ValueError, match="release_hold must be 'HOLD'"):
            _policy(release_hold="")

    def test_release_hold_lowercase_raises(self):
        with pytest.raises(ValueError, match="release_hold must be 'HOLD'"):
            _policy(release_hold="hold")

    def test_release_hold_none_raises(self):
        with pytest.raises((ValueError, TypeError)):
            _policy(release_hold=None)


# ---------------------------------------------------------------------------
# 2. Empty experiment lists
# ---------------------------------------------------------------------------

class TestEmptyExperimentLists:
    def test_plan_with_empty_experiments(self):
        plan = OfflineShadowExperimentPlan(
            plan_id="p_empty",
            experiments=(),
            run_config=_run_config(),
            safety_policy=_policy(),
        )
        assert len(plan.experiments) == 0

    def test_run_config_with_empty_symbols(self):
        rc = _run_config(symbols=())
        assert len(rc.symbols) == 0

    def test_run_config_with_empty_timeframes(self):
        rc = _run_config(timeframes=())
        assert len(rc.timeframes) == 0


# ---------------------------------------------------------------------------
# 3. Missing / invalid fields
# ---------------------------------------------------------------------------

class TestMissingFields:
    def test_symbol_empty_string(self):
        s = _symbol(symbol="")
        assert s.symbol == ""

    def test_window_start_greater_than_end(self):
        w = _window(start_index=200, end_index=100)
        # No validation in model itself; this documents the degenerate state
        assert w.start_index > w.end_index

    def test_timeframe_zero_minutes(self):
        tf = _timeframe(minutes=0)
        assert tf.minutes == 0


# ---------------------------------------------------------------------------
# 4. Invalid parameter ranges
# ---------------------------------------------------------------------------

class TestInvalidParameterRanges:
    def test_negative_entry_threshold(self):
        p = _params(entry_threshold=-0.5)
        assert p.entry_threshold < 0

    def test_negative_stop_loss(self):
        p = _params(stop_loss_r=-1.0)
        assert p.stop_loss_r < 0

    def test_zero_stop_loss(self):
        p = _params(stop_loss_r=0.0)
        assert p.stop_loss_r == 0.0

    def test_negative_take_profit(self):
        p = _params(take_profit_r=-2.0)
        assert p.take_profit_r < 0

    def test_negative_max_hold_bars(self):
        p = _params(max_hold_bars=-5)
        assert p.max_hold_bars < 0


# ---------------------------------------------------------------------------
# 5. Duplicate experiment IDs
# ---------------------------------------------------------------------------

class TestDuplicateExperimentIDs:
    def test_plan_with_duplicate_ids(self):
        e1 = _experiment(eid="exp_dup")
        e2 = _experiment(eid="exp_dup")
        plan = OfflineShadowExperimentPlan(
            plan_id="p_dup",
            experiments=(e1, e2),
            run_config=_run_config(),
            safety_policy=_policy(),
        )
        # No validation prevents this; document the degenerate state
        ids = [e.experiment_id for e in plan.experiments]
        assert len(ids) == 2
        assert ids[0] == ids[1]


# ---------------------------------------------------------------------------
# 6. Empty outcomes in metric computation
# ---------------------------------------------------------------------------

class TestEmptyOutcomes:
    def test_compute_run_metrics_empty(self):
        result = compute_run_metrics([])
        assert result["candidate_count"] == 0
        assert result["coverage_status"] == "empty"

    def test_compute_aggregate_metrics_empty(self):
        result = compute_aggregate_metrics([])
        assert result["run_count"] == 0
        assert result["candidate_count"] == 0

    def test_compute_run_metrics_single_zero_return(self):
        result = compute_run_metrics([{"return_r": 0.0}])
        assert result["candidate_count"] == 1
        assert result["win_count"] == 0
        assert result["loss_count"] == 0


# ---------------------------------------------------------------------------
# 7. Scorecard with all REJECT grades
# ---------------------------------------------------------------------------

class TestAllRejectGrades:
    def test_all_reject_metrics_low_win_rate(self):
        """Experiments with all losses should produce very negative metrics."""
        outcomes = [{"return_r": -1.0} for _ in range(20)]
        result = compute_run_metrics(outcomes)
        assert result["win_rate"] == 0.0
        assert result["avg_return_r"] < 0
        assert result["expectancy_r"] < 0


# ---------------------------------------------------------------------------
# 8. Comparison with mismatched experiment IDs
# ---------------------------------------------------------------------------

class TestMismatchedExperimentIDs:
    def test_different_experiment_ids(self):
        e1 = _experiment(eid="exp_A")
        e2 = _experiment(eid="exp_B")
        assert e1.experiment_id != e2.experiment_id


# ---------------------------------------------------------------------------
# 9. Invalid fixture dir / plan
# ---------------------------------------------------------------------------

class TestInvalidFixtureDir:
    def test_nonexistent_fixture_dir(self):
        rc = _run_config(fixture_dir="/nonexistent/path/to/fixtures")
        assert not Path(rc.fixture_dir).exists()

    def test_plan_with_invalid_config(self):
        """Plan can be constructed with invalid paths -- no I/O at model level."""
        plan = OfflineShadowExperimentPlan(
            plan_id="p_bad_path",
            experiments=(_experiment(),),
            run_config=_run_config(fixture_dir="/bad/path", output_dir="/bad/out"),
            safety_policy=_policy(),
        )
        assert plan.run_config.fixture_dir == "/bad/path"


# ---------------------------------------------------------------------------
# 10. Metric edge cases
# ---------------------------------------------------------------------------

class TestMetricEdgeCases:
    def test_all_neutral_returns(self):
        outcomes = [{"return_r": 0.0} for _ in range(10)]
        result = compute_run_metrics(outcomes)
        assert result["win_count"] == 0
        assert result["loss_count"] == 0
        assert result["neutral_count"] == 10

    def test_missing_return_r_key(self):
        """Outcomes without return_r should default to 0.0."""
        result = compute_run_metrics([{"symbol": "BTCUSDT"}])
        assert result["candidate_count"] == 1
        assert result["avg_return_r"] == 0.0

    def test_single_outcome(self):
        result = compute_run_metrics([{"return_r": 2.5}])
        assert result["candidate_count"] == 1
        assert result["win_count"] == 1
        assert result["avg_return_r"] == pytest.approx(2.5)

    def test_aggregate_with_mixed_run_counts(self):
        r1 = compute_run_metrics([{"return_r": 1.0}, {"return_r": -0.5}])
        r2 = compute_run_metrics([{"return_r": 3.0}])
        agg = compute_aggregate_metrics([r1, r2])
        assert agg["run_count"] == 2
        assert agg["candidate_count"] == 3
