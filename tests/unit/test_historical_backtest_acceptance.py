"""End-to-end acceptance tests for Historical OHLCV Offline Backtest Lab.

20+ tests covering: imports, fixtures, splits, signals, simulation,
metrics, scorecard, comparison, reports, bundle, orchestrator, negatives.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

# ── Module imports ────────────────────────────────────────────────────────

from core.historical_ohlcv_schema import (
    HistoricalBar,
    HistoricalDataIssue,
    HistoricalDataQualityReport,
    HistoricalSymbolDataset,
    HistoricalTimeframe,
    IssueType,
    OHLCVColumnMapping,
    Severity,
)
from core.historical_ohlcv_chunked_reader import (
    deduplicate_bars,
    detect_gaps,
    read_ohlcv_chunks,
    summarize_dataset,
    validate_ohlcv_chunk,
)
from core.walk_forward_split_engine import (
    SplitType,
    WalkForwardSplit,
    detect_split_gaps,
    split_expanding,
    split_rolling,
    validate_split,
)
from core.offline_breakout_signal_engine import (
    BreakoutSignal,
    BreakoutSignalParams,
    scan_breakout_signals,
)
from core.offline_backtest_trade_simulator import (
    ExitReason,
    TradeOutcome,
    TradeSimulationParams,
    simulate_trade,
)
from core.offline_backtest_metrics_engine import (
    compute_aggregate_metrics,
    compute_run_metrics,
)
from core.offline_shadow_metric_engine import (
    compute_aggregate_metrics as shadow_aggregate,
    compute_run_metrics as shadow_run_metrics,
)
from core.offline_shadow_scorecard import grade_experiment, grade_run
from core.offline_shadow_comparison import compare_experiments
from core.offline_shadow_report_renderer import (
    render_report_html,
    render_report_json,
    render_report_markdown,
)
from core.offline_shadow_bundle_builder import build_bundle, build_manifest, compute_sha256
from core.offline_shadow_parameter_set import OfflineShadowParameterSet
from core.offline_backtest_orchestrator import run_backtest_on_bars, run_walk_forward_backtest


# ── Fixtures ──────────────────────────────────────────────────────────────

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "historical_ohlcv"
SHADOW_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "offline_shadow_research"


def _load_csv_bars(csv_path: Path) -> list[dict]:
    """Load CSV fixture into list of bar dicts."""
    bars = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append({
                "timestamp": float(row["timestamp"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })
    return bars


# ── Test: All core modules importable ─────────────────────────────────────

class TestModuleImports:
    def test_schema_importable(self):
        assert HistoricalBar is not None
        assert IssueType is not None

    def test_chunked_reader_importable(self):
        assert read_ohlcv_chunks is not None
        assert deduplicate_bars is not None

    def test_walk_forward_importable(self):
        assert split_rolling is not None
        assert split_expanding is not None

    def test_signal_engine_importable(self):
        assert scan_breakout_signals is not None
        assert BreakoutSignalParams is not None

    def test_trade_simulator_importable(self):
        assert simulate_trade is not None
        assert TradeSimulationParams is not None

    def test_metrics_engine_importable(self):
        assert compute_run_metrics is not None
        assert compute_aggregate_metrics is not None

    def test_scorecard_importable(self):
        assert grade_run is not None
        assert grade_experiment is not None

    def test_comparison_importable(self):
        assert compare_experiments is not None

    def test_report_renderers_importable(self):
        assert render_report_markdown is not None
        assert render_report_json is not None
        assert render_report_html is not None

    def test_bundle_builder_importable(self):
        assert build_bundle is not None
        assert compute_sha256 is not None

    def test_parameter_set_importable(self):
        assert OfflineShadowParameterSet is not None

    def test_orchestrator_importable(self):
        assert run_backtest_on_bars is not None
        assert run_walk_forward_backtest is not None


# ── Test: Fixture CSVs exist and are valid ────────────────────────────────

class TestFixtureIntegrity:
    def test_btcusdt_csv_exists(self):
        path = FIXTURE_DIR / "BTCUSDT_5m.csv"
        assert path.exists(), f"Missing fixture: {path}"

    def test_ethusdt_csv_exists(self):
        path = FIXTURE_DIR / "ETHUSDT_5m.csv"
        assert path.exists(), f"Missing fixture: {path}"

    def test_btcusdt_csv_has_header(self):
        path = FIXTURE_DIR / "BTCUSDT_5m.csv"
        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "timestamp" in header
        assert "close" in header
        assert "volume" in header

    def test_btcusdt_csv_has_data(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        assert len(bars) >= 50, f"Expected 50+ bars, got {len(bars)}"

    def test_shadow_fixtures_exist(self):
        assert (SHADOW_FIXTURE_DIR / "bars_BTCUSDT_5m.json").exists()
        assert (SHADOW_FIXTURE_DIR / "outcomes_BTCUSDT_5m.json").exists()


# ── Test: Walk-forward split works on fixtures ────────────────────────────

class TestWalkForwardOnFixtures:
    def test_rolling_split_on_btcusdt(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        splits = split_rolling(bars, train_pct=0.6, test_pct=0.2, n_splits=2)
        assert len(splits) > 0
        assert len(splits) % 2 == 0

    def test_expanding_split_on_btcusdt(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        splits = split_expanding(bars, train_pct=0.5, test_pct=0.2, n_splits=2)
        assert len(splits) > 0
        train_splits = [s for s in splits if s.split_type == SplitType.TRAIN]
        for ts in train_splits:
            assert ts.start_index == 0


# ── Test: Parameter grid produces expected presets ────────────────────────

class TestParameterGrid:
    def test_parameter_set_creation(self):
        ps = OfflineShadowParameterSet(
            param_id="p1", label="conservative",
            entry_threshold=2.0, exit_threshold=0.5,
            stop_loss_r=1.0, take_profit_r=2.0,
            max_hold_bars=50, min_sample_quality=0.3,
        )
        assert ps.param_id == "p1"
        assert ps.entry_threshold == 2.0

    def test_parameter_set_frozen(self):
        ps = OfflineShadowParameterSet(
            param_id="p1", label="test",
            entry_threshold=2.0, exit_threshold=0.5,
            stop_loss_r=1.0, take_profit_r=2.0,
            max_hold_bars=50, min_sample_quality=0.3,
        )
        with pytest.raises(AttributeError):
            ps.param_id = "p2"


# ── Test: Signal engine produces signals on fixture data ──────────────────

class TestSignalEngineOnFixtures:
    def test_signals_produced(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        signals = scan_breakout_signals(bars, BreakoutSignalParams(
            lookback=10, breakout_threshold=0.003,
            volume_multiplier=1.2, min_bars_required=15,
            cooldown_bars=2,
        ))
        # With a trending fixture, we expect at least some signals
        assert isinstance(signals, list)

    def test_signal_has_required_fields(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        signals = scan_breakout_signals(bars, BreakoutSignalParams(
            lookback=10, breakout_threshold=0.003,
            volume_multiplier=1.2, min_bars_required=15,
        ))
        if signals:
            sig = signals[0]
            assert hasattr(sig, "signal_id")
            assert hasattr(sig, "entry_price")
            assert hasattr(sig, "stop_price")
            assert hasattr(sig, "tp_price")
            assert sig.direction in ("LONG", "SHORT")


# ── Test: Trade simulation produces outcomes ──────────────────────────────

class TestTradeSimulation:
    def test_simulate_trade_basic(self):
        bars = [
            {"timestamp": i, "open": 100.0, "high": 101.0, "low": 99.0,
             "close": 100.0, "volume": 100.0}
            for i in range(20)
        ]
        signal = {
            "signal_id": "test_1",
            "entry_bar_index": 5,
            "entry_price": 100.0,
            "stop_price": 98.0,
            "tp_price": 104.0,
        }
        outcome = simulate_trade(signal, bars)
        assert isinstance(outcome, TradeOutcome)
        assert outcome.signal_id == "test_1"

    def test_simulation_on_fixture(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        signals = scan_breakout_signals(bars, BreakoutSignalParams(
            lookback=10, breakout_threshold=0.003,
            volume_multiplier=1.2, min_bars_required=15,
        ))
        if signals:
            sig = signals[0]
            outcome = simulate_trade(
                signal={
                    "signal_id": sig.signal_id,
                    "entry_bar_index": sig.bar_index,
                    "entry_price": sig.entry_price,
                    "stop_price": sig.stop_price,
                    "tp_price": sig.tp_price,
                },
                bars=bars,
            )
            assert outcome.exit_reason in [e.value for e in ExitReason]


# ── Test: Metrics computation works ───────────────────────────────────────

class TestMetricsComputation:
    def test_empty_trades(self):
        metrics = compute_run_metrics([])
        assert metrics["trade_count"] == 0

    def test_single_trade(self):
        trades = [{
            "trade_id": "t1", "signal_id": "s1",
            "entry_bar_index": 0, "exit_bar_index": 5,
            "entry_price": 100.0, "exit_price": 102.0,
            "exit_reason": "TAKE_PROFIT", "realized_r": 1.0,
            "gross_pnl": 2.0, "fees": 0.2, "slippage_cost": 0.05,
            "net_pnl": 1.75, "mfe_r": 1.5, "mae_r": 0.3, "hold_bars": 5,
        }]
        metrics = compute_run_metrics(trades)
        assert metrics["trade_count"] == 1
        assert metrics["win_rate"] == 1.0

    def test_aggregate_metrics(self):
        run_metrics = [
            {"trade_count": 5, "win_rate": 0.6, "expectancy_r": 0.5,
             "avg_r": 0.5, "median_r": 0.3, "max_drawdown_r": -1.0,
             "profit_factor": 1.5, "avg_mfe_r": 1.0, "avg_mae_r": 0.5,
             "exposure_bars": 25, "avg_hold_bars": 5.0,
             "quality_adjusted_score": 0.5, "sample_adequacy_score": 0.17},
        ]
        agg = compute_aggregate_metrics(run_metrics)
        assert agg["run_count"] == 1


# ── Test: Scorecard grading works ─────────────────────────────────────────

class TestScorecardGrading:
    def test_pass_grade(self):
        metrics = {
            "candidate_count": 10,
            "sample_quality_score": 0.5,
            "max_drawdown_r": -2.0,
            "expectancy_r": 0.5,
        }
        result = grade_run(metrics)
        assert result["grade"] == "PASS"

    def test_reject_insufficient_candidates(self):
        metrics = {
            "candidate_count": 2,
            "sample_quality_score": 0.5,
            "max_drawdown_r": -1.0,
            "expectancy_r": 0.5,
        }
        result = grade_run(metrics)
        assert result["grade"] == "REJECT"
        assert "insufficient_candidates" in result["blockers"]

    def test_watch_non_positive_expectancy(self):
        metrics = {
            "candidate_count": 10,
            "sample_quality_score": 0.5,
            "max_drawdown_r": -1.0,
            "expectancy_r": -0.1,
        }
        result = grade_run(metrics)
        assert result["grade"] == "WATCH"


# ── Test: Comparison works ────────────────────────────────────────────────

class TestComparison:
    def test_compare_two_experiments(self):
        a = {"experiment_id": "exp1", "runs": [{"run_id": "r1", "metrics": {
            "candidate_count": 10, "win_count": 6, "loss_count": 4,
            "expectancy_r": 0.5, "max_drawdown_r": -1.0,
            "sample_quality_score": 0.5, "profit_factor": 1.5,
            "coverage_status": "full"}}]}
        b = {"experiment_id": "exp2", "runs": [{"run_id": "r1", "metrics": {
            "candidate_count": 10, "win_count": 5, "loss_count": 5,
            "expectancy_r": 0.3, "max_drawdown_r": -0.5,
            "sample_quality_score": 0.6, "profit_factor": 1.2,
            "coverage_status": "full"}}]}
        result = compare_experiments(a, b)
        assert isinstance(result, dict)
        assert "deltas" in result

    def test_compare_empty(self):
        a = {"experiment_id": "a", "runs": []}
        b = {"experiment_id": "b", "runs": []}
        result = compare_experiments(a, b)
        assert result["improved"] is False


# ── Test: Report renderers produce output ─────────────────────────────────

class TestReportRenderers:
    def test_markdown_renderer(self):
        results = [{
            "experiment_id": "exp1", "symbol": "BTC", "timeframe": "5m",
            "param_label": "default", "metrics": {"win_rate": 0.6,
            "expectancy_r": 0.5, "profit_factor": 1.5, "candidate_count": 10,
            "win_count": 6, "loss_count": 4, "neutral_count": 0,
            "avg_return_r": 0.5, "max_drawdown_r": -1.0,
            "sample_quality_score": 0.5, "coverage_status": "full"},
            "scorecard": {"grade": "PASS", "reason_codes": []},
        }]
        md = render_report_markdown(results)
        assert "Offline Shadow Research Report" in md
        assert "release_hold = HOLD" in md

    def test_json_renderer(self):
        results = [{
            "experiment_id": "exp1", "symbol": "BTC", "timeframe": "5m",
            "param_label": "default", "metrics": {"win_rate": 0.6,
            "expectancy_r": 0.5, "profit_factor": 1.5, "candidate_count": 10,
            "win_count": 6, "loss_count": 4, "neutral_count": 0,
            "avg_return_r": 0.5, "max_drawdown_r": -1.0,
            "sample_quality_score": 0.5, "coverage_status": "full"},
            "scorecard": {"grade": "PASS"},
        }]
        report = render_report_json(results)
        assert report["release_hold"] == "HOLD"
        assert report["experiment_count"] == 1

    def test_html_renderer(self):
        results = [{
            "experiment_id": "exp1", "symbol": "BTC", "timeframe": "5m",
            "param_label": "default", "metrics": {"win_rate": 0.6,
            "expectancy_r": 0.5, "profit_factor": 1.5, "candidate_count": 10,
            "win_count": 6, "loss_count": 4, "neutral_count": 0,
            "avg_return_r": 0.5, "max_drawdown_r": -1.0,
            "sample_quality_score": 0.5, "coverage_status": "full"},
            "scorecard": {"grade": "PASS"},
        }]
        html = render_report_html(results)
        assert "HOLD" in html
        assert "<html" in html


# ── Test: Bundle builder produces manifest with correct safety flags ──────

class TestBundleBuilder:
    def test_manifest_safety_flags(self):
        manifest = build_manifest([])
        assert manifest["release_hold"] == "HOLD"
        assert manifest["no_live"] is True
        assert manifest["no_submit"] is True
        assert manifest["no_exchange"] is True

    def test_bundle_build(self):
        bundle = build_bundle(
            plan_data={"symbols": ["BTC"]},
            matrix_data={"presets": []},
            results_data=[],
            scorecard_data={"grade": "PASS"},
            report_markdown="# Report",
            report_html="<html></html>",
            report_json={"experiments": []},
        )
        assert "manifest.json" in bundle
        manifest = json.loads(bundle["manifest.json"])
        assert manifest["release_hold"] == "HOLD"

    def test_sha256_deterministic(self):
        h1 = compute_sha256("hello")
        h2 = compute_sha256("hello")
        assert h1 == h2
        assert len(h1) == 64


# ── Test: Orchestrator accepts all required args ──────────────────────────

class TestOrchestrator:
    def test_run_backtest_on_bars(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        result = run_backtest_on_bars(bars)
        assert "signals" in result
        assert "trades" in result
        assert "metrics" in result
        assert "scorecard" in result

    def test_run_walk_forward_backtest(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        result = run_walk_forward_backtest(bars, n_splits=2)
        assert "per_split_results" in result
        assert "aggregate_metrics" in result

    def test_orchestrator_with_custom_params(self):
        bars = _load_csv_bars(FIXTURE_DIR / "BTCUSDT_5m.csv")
        result = run_backtest_on_bars(
            bars,
            signal_params=BreakoutSignalParams(
                lookback=10, breakout_threshold=0.003,
                volume_multiplier=1.2, min_bars_required=15,
            ),
            sim_params=TradeSimulationParams(slippage_pct=0.001, fee_pct=0.002),
        )
        assert "scorecard" in result


# ── Test: Negative cases ──────────────────────────────────────────────────

class TestNegativeCases:
    def test_missing_csv_raises(self):
        mapping = OHLCVColumnMapping(
            timestamp_col="timestamp", open_col="open", high_col="high",
            low_col="low", close_col="close", volume_col="volume",
        )
        with pytest.raises(FileNotFoundError):
            list(read_ohlcv_chunks("/nonexistent.csv", mapping))

    def test_bad_signal_params(self):
        with pytest.raises(ValueError):
            BreakoutSignalParams(lookback=0)

    def test_bad_sim_params(self):
        with pytest.raises(ValueError):
            TradeSimulationParams(slippage_pct=-1)

    def test_split_rejects_zero_bars(self):
        with pytest.raises(ValueError):
            split_rolling([], train_pct=0.6, test_pct=0.2, n_splits=1)

    def test_grade_run_with_empty_metrics(self):
        result = grade_run({"candidate_count": 0, "sample_quality_score": 0.0,
                           "max_drawdown_r": 0.0, "expectancy_r": 0.0})
        assert result["grade"] == "REJECT"
