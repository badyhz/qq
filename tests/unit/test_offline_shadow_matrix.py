import pytest

from core.offline_shadow_experiment import OfflineShadowExperiment
from core.offline_shadow_experiment_plan import OfflineShadowExperimentPlan
from core.offline_shadow_matrix_materializer import materialize_replay_matrix
from core.offline_shadow_parameter_set import OfflineShadowParameterSet
from core.offline_shadow_run_config import OfflineShadowRunConfig
from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
from core.offline_shadow_symbol import OfflineShadowSymbol
from core.offline_shadow_timeframe import OfflineShadowTimeframe
from core.offline_shadow_window import OfflineShadowWindow


FIXTURE_DIR = "/tmp/test_fixtures"


def _make_plan(n_symbols=2, n_tf=2, n_windows=3, n_params=3):
    symbols = ["BTCUSDT", "ETHUSDT"][:n_symbols]
    timeframes = ["5m", "15m"][:n_tf]
    windows = ["train", "validation", "test"][:n_windows]
    param_names = ["conservative", "balanced", "aggressive"][:n_params]

    window_defs = {
        "train": ("train", 0, 100),
        "validation": ("validation", 100, 150),
        "test": ("test", 150, 200),
    }
    param_defs = {
        "conservative": (0.75, 0.30, 1.5, 3.0, 20, 0.85),
        "balanced": (0.60, 0.25, 2.0, 2.5, 15, 0.70),
        "aggressive": (0.45, 0.20, 2.5, 2.0, 10, 0.55),
    }
    tf_mins = {"5m": 5, "15m": 15}

    safety = OfflineShadowSafetyPolicy(
        no_live=True, no_submit=True, no_exchange=True, release_hold="HOLD"
    )

    experiments = []
    idx = 0
    for sym in symbols:
        for tf in timeframes:
            for w in windows:
                for p in param_names:
                    wt, ws, we = window_defs[w]
                    et, ex, sl, tp, mh, ms = param_defs[p]
                    exp = OfflineShadowExperiment(
                        experiment_id=f"exp_{idx:04d}",
                        symbol=OfflineShadowSymbol(sym, sym[:3], sym[3:], "binance"),
                        timeframe=OfflineShadowTimeframe(tf, tf_mins[tf]),
                        window=OfflineShadowWindow(f"w_{w}", wt, ws, we),
                        parameter_set=OfflineShadowParameterSet(
                            f"p_{p}", p, et, ex, sl, tp, mh, ms
                        ),
                        safety_policy=safety,
                    )
                    experiments.append(exp)
                    idx += 1

    rc = OfflineShadowRunConfig(
        config_id="test_plan",
        symbols=tuple(symbols),
        timeframes=tuple(timeframes),
        windows=tuple(windows),
        param_grid=tuple(param_names),
        fixture_dir=FIXTURE_DIR,
        output_dir="/tmp/output",
    )

    return OfflineShadowExperimentPlan(
        plan_id="test_plan",
        experiments=tuple(experiments),
        run_config=rc,
        safety_policy=safety,
    )


class TestMatrixRunCount:
    def test_full_grid(self):
        plan = _make_plan()
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        assert matrix["run_count"] == 36
        assert len(matrix["runs"]) == 36

    def test_single_combo(self):
        plan = _make_plan(n_symbols=1, n_tf=1, n_windows=1, n_params=1)
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        assert matrix["run_count"] == 1

    def test_custom_combo(self):
        plan = _make_plan(n_symbols=2, n_tf=1, n_windows=2, n_params=3)
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        assert matrix["run_count"] == 12


class TestRunFields:
    REQUIRED_KEYS = {
        "run_id",
        "experiment_id",
        "symbol",
        "base_asset",
        "quote_asset",
        "exchange",
        "timeframe",
        "timeframe_minutes",
        "window_id",
        "window_type",
        "window_start_index",
        "window_end_index",
        "param_id",
        "param_label",
        "entry_threshold",
        "exit_threshold",
        "stop_loss_r",
        "take_profit_r",
        "max_hold_bars",
        "min_sample_quality",
        "fixture_bars",
        "fixture_signals",
        "fixture_outcomes",
        "safety",
    }

    def test_all_runs_have_required_fields(self):
        plan = _make_plan()
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        for run in matrix["runs"]:
            assert set(run.keys()) == self.REQUIRED_KEYS, (
                f"Missing keys: {self.REQUIRED_KEYS - set(run.keys())}"
            )

    def test_run_id_format(self):
        plan = _make_plan(n_symbols=1, n_tf=1, n_windows=1, n_params=1)
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        run = matrix["runs"][0]
        assert run["run_id"] == "run_exp_0000"

    def test_fixture_refs_format(self):
        plan = _make_plan(n_symbols=1, n_tf=1, n_windows=1, n_params=1)
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        run = matrix["runs"][0]
        assert run["fixture_bars"] == "bars_BTCUSDT_5m.json"
        assert run["fixture_signals"] == "signals_BTCUSDT_5m.json"
        assert run["fixture_outcomes"] == "outcomes_BTCUSDT_5m.json"


class TestDeterminism:
    def test_same_plan_same_matrix(self):
        plan = _make_plan()
        m1 = materialize_replay_matrix(plan, FIXTURE_DIR)
        m2 = materialize_replay_matrix(plan, FIXTURE_DIR)
        assert m1 == m2

    def test_run_order_stable(self):
        plan = _make_plan()
        m1 = materialize_replay_matrix(plan, FIXTURE_DIR)
        m2 = materialize_replay_matrix(plan, FIXTURE_DIR)
        ids1 = [r["run_id"] for r in m1["runs"]]
        ids2 = [r["run_id"] for r in m2["runs"]]
        assert ids1 == ids2


class TestSafetyFlags:
    def test_all_runs_have_hold(self):
        plan = _make_plan()
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        for run in matrix["runs"]:
            assert run["safety"]["release_hold"] == "HOLD"
            assert run["safety"]["no_live"] is True
            assert run["safety"]["no_submit"] is True
            assert run["safety"]["no_exchange"] is True

    def test_top_level_safety(self):
        plan = _make_plan()
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        assert matrix["safety_policy"]["release_hold"] == "HOLD"

    def test_fixture_dir_preserved(self):
        plan = _make_plan()
        matrix = materialize_replay_matrix(plan, FIXTURE_DIR)
        assert matrix["fixture_dir"] == FIXTURE_DIR
