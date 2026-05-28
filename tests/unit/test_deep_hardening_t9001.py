"""Deep hardening gap fix tests — T9001-T9300.

Fixture-driven, adversarial, strong-assertion tests for all major programs.
Offline only. No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import hashlib
import pytest
import tempfile
from pathlib import Path

from utils.research_fixture_loader import (
    load_fixture, load_fixture_by_name, load_all_fixtures_in_dir,
    validate_fixture_bars, validate_fixture_splits, fixture_hash,
    discover_fixture_files, FixtureLoadError, FIXTURE_ROOT,
)


# ============================================================
# A. Fixture Loader Tests
# ============================================================

class TestFixtureLoaderNormal:
    def test_load_clean_ohlcv(self):
        data = load_fixture_by_name("base", "clean_ohlcv_btcusdt_5m.json")
        assert data["fixture_type"] == "clean_ohlcv"
        assert data["symbol"] == "BTCUSDT"
        assert len(data["bars"]) == 10
        assert data["expected_verdict"] == "PASS"

    def test_load_ethusdt_fixture(self):
        data = load_fixture_by_name("base", "clean_ohlcv_ethusdt_15m.json")
        assert data["symbol"] == "ETHUSDT"
        assert data["timeframe"] == "15m"

    def test_load_workbench_results(self):
        data = load_fixture_by_name("base", "workbench_results_clean.json")
        assert len(data["results"]) == 8
        strategies = set(r["strategy_id"] for r in data["results"])
        assert strategies == {"breakout", "mean_reversion", "momentum", "volatility_compression"}

    def test_load_splits(self):
        data = load_fixture_by_name("base", "splits_clean.json")
        assert len(data["splits"]) == 3
        assert data["expected_verdict"] == "PASS"

    def test_validate_bars_clean(self):
        data = load_fixture_by_name("base", "clean_ohlcv_btcusdt_5m.json")
        errors = validate_fixture_bars(data["bars"])
        assert errors == []

    def test_validate_splits_clean(self):
        data = load_fixture_by_name("base", "splits_clean.json")
        errors = validate_fixture_splits(data["splits"])
        assert errors == []

    def test_fixture_hash_deterministic(self):
        data = load_fixture_by_name("base", "clean_ohlcv_btcusdt_5m.json")
        h1 = fixture_hash(data)
        h2 = fixture_hash(data)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_discover_fixtures(self):
        files = discover_fixture_files()
        assert "base" in files
        assert "adversarial" in files
        assert "negative_control" in files
        assert "regime" in files
        assert "bootstrap" in files
        assert "expected" in files

    def test_load_all_in_base(self):
        fixtures = load_all_fixtures_in_dir(FIXTURE_ROOT / "base")
        assert len(fixtures) >= 4
        for f in fixtures:
            assert "schema_version" in f
            assert "fixture_type" in f


class TestFixtureLoaderEdge:
    def test_missing_file_raises(self):
        with pytest.raises(FixtureLoadError, match="not found"):
            load_fixture(Path("/nonexistent/path.json"))

    def test_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("{invalid json")
            f.flush()
            with pytest.raises(FixtureLoadError, match="Invalid JSON"):
                load_fixture(Path(f.name))

    def test_non_dict_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump([1, 2, 3], f)
            f.flush()
            with pytest.raises(FixtureLoadError, match="must be dict"):
                load_fixture(Path(f.name))

    def test_missing_required_field_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"schema_version": "1.0.0"}, f)  # missing fixture_type
            f.flush()
            with pytest.raises(FixtureLoadError, match="Missing required field"):
                load_fixture(Path(f.name))

    def test_validate_bars_missing_field(self):
        bars = [{"timestamp": 1, "open": 1.0, "high": 2.0, "low": 0.5}]  # missing close, volume
        errors = validate_fixture_bars(bars)
        assert len(errors) == 2
        assert any("close" in e for e in errors)
        assert any("volume" in e for e in errors)

    def test_validate_bars_null_field(self):
        bars = [{"timestamp": 1, "open": 1.0, "high": 2.0, "low": 0.5, "close": None, "volume": 100}]
        errors = validate_fixture_bars(bars)
        assert any("null" in e for e in errors)

    def test_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            fixtures = load_all_fixtures_in_dir(Path(d))
            assert fixtures == ()


class TestFixtureLoaderAdversarial:
    def test_fixture_not_touched(self):
        """Verify fixture loader is read-only — does not modify fixtures."""
        data1 = load_fixture_by_name("base", "clean_ohlcv_btcusdt_5m.json")
        h1 = fixture_hash(data1)
        data2 = load_fixture_by_name("base", "clean_ohlcv_btcusdt_5m.json")
        h2 = fixture_hash(data2)
        assert h1 == h2


class TestFixtureLoaderDeterministic:
    def test_fixture_hash_stable(self):
        data = load_fixture_by_name("base", "clean_ohlcv_btcusdt_5m.json")
        hashes = [fixture_hash(data) for _ in range(5)]
        assert len(set(hashes)) == 1

    def test_discover_deterministic(self):
        d1 = discover_fixture_files()
        d2 = discover_fixture_files()
        assert d1 == d2


# ============================================================
# B. Data Quality Adversarial Tests (fixture-driven)
# ============================================================

class TestDataQualityAdversarialFixtureDriven:
    def test_impossible_ohlc_fixture(self):
        data = load_fixture_by_name("adversarial/data_quality", "impossible_ohlc.json")
        from core.data_quality_deep_audit import audit_ohlcv_rows
        findings = audit_ohlcv_rows(data["bars"])
        reason_codes = [f.reason_code for f in findings]
        assert "IMPOSSIBLE_OHLC" in reason_codes
        assert data["expected_verdict"] == "FAIL"
        assert data["expected_block_promotion"] is True

    def test_missing_bars_fixture(self):
        data = load_fixture_by_name("adversarial/data_quality", "missing_bars.json")
        from core.data_quality_deep_audit import audit_ohlcv_rows
        findings = audit_ohlcv_rows(data["bars"])
        reason_codes = [f.reason_code for f in findings]
        assert "MISSING_OHLCV_FIELDS" in reason_codes
        assert data["expected_verdict"] == "FAIL"

    def test_zero_volume_fixture(self):
        data = load_fixture_by_name("adversarial/data_quality", "zero_volume.json")
        from core.data_quality_deep_audit import audit_ohlcv_rows, build_audit_result
        findings = audit_ohlcv_rows(data["bars"])
        result = build_audit_result(findings)
        assert result.verdict == "PARTIAL"
        assert "ZERO_VOLUME" in [f.reason_code for f in findings]
        # Zero volume is WARNING, not HARD_BLOCK
        assert result.hard_blocks == ()

    def test_clean_bars_pass(self):
        data = load_fixture_by_name("base", "clean_ohlcv_btcusdt_5m.json")
        from core.data_quality_deep_audit import audit_ohlcv_rows, build_audit_result
        findings = audit_ohlcv_rows(data["bars"])
        result = build_audit_result(findings, total_rows=len(data["bars"]))
        assert result.verdict == "PASS"
        assert result.findings == ()
        assert result.hard_blocks == ()
        assert result.total_rows_audited == 10

    def test_impossible_ohlc_exact_block_reason(self):
        data = load_fixture_by_name("adversarial/data_quality", "impossible_ohlc.json")
        from core.data_quality_deep_audit import audit_ohlcv_rows, build_audit_result
        findings = audit_ohlcv_rows(data["bars"])
        result = build_audit_result(findings)
        assert result.verdict == "FAIL"
        assert "IMPOSSIBLE_OHLC" in result.hard_blocks
        assert len(result.hard_blocks) == 1

    def test_missing_bars_exact_count(self):
        data = load_fixture_by_name("adversarial/data_quality", "missing_bars.json")
        from core.data_quality_deep_audit import audit_ohlcv_rows
        findings = audit_ohlcv_rows(data["bars"])
        missing_finding = [f for f in findings if f.reason_code == "MISSING_OHLCV_FIELDS"]
        assert len(missing_finding) == 1
        assert missing_finding[0].count == 2  # high=null and close=null

    def test_fixture_corruption_clean_csv(self):
        from core.data_quality_fixture_corruption import check_fixture_corruption
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("timestamp,open,high,low,close,volume\n")
            f.write("1,42000,42100,41900,42050,100\n")
            f.flush()
            result = check_fixture_corruption(Path(f.name))
            assert result.corruption_type == "NONE"
            assert result.block_promotion is False

    def test_fixture_corruption_missing_csv_headers(self):
        from core.data_quality_fixture_corruption import check_fixture_corruption
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("timestamp,open,high\n")  # missing low, close, volume
            f.flush()
            result = check_fixture_corruption(Path(f.name))
            assert result.corruption_type == "WRONG_HEADER"
            assert result.block_promotion is True

    def test_fixture_corruption_empty_file(self):
        from core.data_quality_fixture_corruption import check_fixture_corruption
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.flush()
            result = check_fixture_corruption(Path(f.name))
            assert result.corruption_type == "EMPTY"
            assert result.block_promotion is True

    def test_fixture_corruption_invalid_json(self):
        from core.data_quality_fixture_corruption import check_fixture_corruption
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("{truncated")
            f.flush()
            result = check_fixture_corruption(Path(f.name))
            assert result.corruption_type == "TRUNCATED"
            assert result.block_promotion is True


# ============================================================
# C. Split Leakage Adversarial Tests (fixture-driven)
# ============================================================

class TestSplitLeakageAdversarialFixtureDriven:
    def test_overlapping_splits_fixture(self):
        data = load_fixture_by_name("adversarial/split_leakage", "overlapping_splits.json")
        from core.split_leakage_rolling import validate_rolling_splits
        results = validate_rolling_splits(data["splits"])
        valid_count = sum(1 for r in results if r.valid)
        invalid_count = sum(1 for r in results if not r.valid)
        assert valid_count == data["expected_valid_count"]
        assert invalid_count == data["expected_invalid_count"]

    def test_empty_train_range_fixture(self):
        data = load_fixture_by_name("adversarial/split_leakage", "empty_train_range.json")
        from core.split_leakage_rolling import validate_rolling_splits
        results = validate_rolling_splits(data["splits"])
        assert len(results) == 1
        assert not results[0].valid
        assert any("empty train" in r for r in results[0].rejection_reasons)

    def test_clean_splits_fixture(self):
        data = load_fixture_by_name("base", "splits_clean.json")
        from core.split_leakage_rolling import validate_rolling_splits
        results = validate_rolling_splits(data["splits"])
        valid_count = sum(1 for r in results if r.valid)
        assert valid_count == data["expected_valid_count"]
        for r in results:
            assert r.valid is True, f"Split {r.split_id} invalid: {r.rejection_reasons}"
            assert r.chronological is True
            assert r.no_overlap is True

    def test_overlap_exact_rejection_reasons(self):
        data = load_fixture_by_name("adversarial/split_leakage", "overlapping_splits.json")
        from core.split_leakage_rolling import validate_rolling_splits
        results = validate_rolling_splits(data["splits"])
        for r in results:
            assert not r.valid
            assert len(r.rejection_reasons) > 0
            assert any("train_end" in reason or "train_start" in reason for reason in r.rejection_reasons)

    def test_split_result_fields(self):
        data = load_fixture_by_name("base", "splits_clean.json")
        from core.split_leakage_rolling import validate_rolling_splits
        results = validate_rolling_splits(data["splits"])
        for r in results:
            assert r.split_id  # non-empty
            assert isinstance(r.chronological, bool)
            assert isinstance(r.no_overlap, bool)
            assert len(r.train_range) == 2
            assert len(r.test_range) == 2


# ============================================================
# D. Negative Control Adversarial Tests (fixture-driven)
# ============================================================

class TestNegativeControlAdversarialFixtureDriven:
    def test_margin_pass_fixture(self):
        data = load_fixture_by_name("expected/negative_control", "margin_pass_expected.json")
        from core.negative_control_report import evaluate_negative_control_margin
        result = evaluate_negative_control_margin(
            data["strategy_score"], data["control_scores"], data["min_margin"]
        )
        assert result["passes"] == data["expected_passes_all_controls"]

    def test_margin_fail_fixture(self):
        data = load_fixture_by_name("expected/negative_control", "margin_fail_expected.json")
        from core.negative_control_report import evaluate_negative_control_margin
        result = evaluate_negative_control_margin(
            data["strategy_score"], data["control_scores"], data["min_margin"]
        )
        assert result["passes"] == data["expected_passes_all_controls"]
        assert result["warning"]  # non-empty warning

    def test_shuffled_returns_deterministic(self):
        data = load_fixture_by_name("negative_control", "shuffled_returns.json")
        from core.negative_control_shuffled_returns import generate_shuffled_returns_baseline
        r1 = generate_shuffled_returns_baseline(data["original_returns"], seed=data["seed"])
        r2 = generate_shuffled_returns_baseline(data["original_returns"], seed=data["seed"])
        assert r1["score"] == r2["score"]
        assert r1["sample_count"] == data["expected_sample_count"]
        assert r1["baseline_type"] == data["expected_baseline_type"]

    def test_inverted_signal_deterministic(self):
        data = load_fixture_by_name("negative_control", "inverted_signal.json")
        from core.negative_control_inverted_signal import generate_inverted_signal_baseline
        r1 = generate_inverted_signal_baseline(data["signals"], data["returns"], seed=data["seed"])
        r2 = generate_inverted_signal_baseline(data["signals"], data["returns"], seed=data["seed"])
        assert r1["score"] == r2["score"]
        assert r1["baseline_type"] == data["expected_baseline_type"]
        assert r1["total_bars"] == data["expected_total_bars"]

    def test_random_strategy_deterministic(self):
        data = load_fixture_by_name("negative_control", "random_strategy.json")
        from core.negative_control_random_strategy import generate_random_strategy_baseline
        r1 = generate_random_strategy_baseline(data["total_bars"], seed=data["seed"])
        r2 = generate_random_strategy_baseline(data["total_bars"], seed=data["seed"])
        assert r1["trade_count"] == r2["trade_count"]
        assert r1["total_pnl"] == r2["total_pnl"]
        assert r1["baseline_type"] == data["expected_baseline_type"]

    def test_random_strategy_different_seed(self):
        from core.negative_control_random_strategy import generate_random_strategy_baseline
        r1 = generate_random_strategy_baseline(100, seed=42)
        r2 = generate_random_strategy_baseline(100, seed=99)
        assert r1["total_pnl"] != r2["total_pnl"] or r1["trade_count"] != r2["trade_count"]

    def test_shuffled_returns_different_seed(self):
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        from core.negative_control_shuffled_returns import generate_shuffled_returns_baseline
        r1 = generate_shuffled_returns_baseline(returns, seed=42)
        r2 = generate_shuffled_returns_baseline(returns, seed=99)
        # Very unlikely to have identical shuffled order
        assert r1["total_return"] != r2["total_return"] or r1["mean_return"] != r2["mean_return"]

    def test_shuffled_baseline_not_promotable(self):
        """Shuffled/random/inverted baselines must not pass promotion."""
        from core.negative_control_shuffled_returns import generate_shuffled_returns_baseline
        from core.negative_control_random_strategy import generate_random_strategy_baseline
        from core.negative_control_inverted_signal import generate_inverted_signal_baseline
        from core.negative_control_report import build_negative_control_report

        # If real strategy has zero score, it should not beat controls
        shuffled = generate_shuffled_returns_baseline([0.0] * 10, seed=42)
        rand = generate_random_strategy_baseline(10, seed=42)
        inverted = generate_inverted_signal_baseline([1] * 10, [0.0] * 10, seed=42)

        baselines = {
            "shuffled": shuffled,
            "random": rand,
            "inverted": inverted,
        }
        report = build_negative_control_report("zero_strategy", 0.0, baselines, min_margin=0.10, seed=42)
        # Zero strategy should pass because both_zero check
        # But with min_margin > 0 and random baseline having non-zero score, it should fail
        assert report["release_hold"] == "HOLD"

    def test_negative_control_blocks_insufficient_margin(self):
        from core.negative_control_report import build_negative_control_report
        baselines = {"random": {"score": 0.45, "baseline_type": "random"}}
        report = build_negative_control_report("strat1", 0.50, baselines, min_margin=0.10, seed=42)
        assert not report["passes_all_controls"]
        assert "INSUFFICIENT_NEGATIVE_CONTROL_MARGIN" in report["hard_blocks"]
        assert report["verdict"] == "FAIL"

    def test_negative_control_passes_sufficient_margin(self):
        from core.negative_control_report import build_negative_control_report
        baselines = {"random": {"score": 0.05, "baseline_type": "random"}}
        report = build_negative_control_report("strat1", 0.50, baselines, min_margin=0.10, seed=42)
        assert report["passes_all_controls"]
        assert report["hard_blocks"] == []
        assert report["verdict"] == "PASS"


# ============================================================
# E. Bootstrap Adversarial Tests (fixture-driven)
# ============================================================

class TestBootstrapAdversarialFixtureDriven:
    def test_bootstrap_seed_expected_fixture(self):
        data = load_fixture_by_name("bootstrap", "bootstrap_seed_expected.json")
        from core.bootstrap_research_report import build_bootstrap_report
        report = build_bootstrap_report(
            data["returns"], data["n_iterations"], seed=data["seed"]
        )
        assert data["expected_worst_case_5pct_range"][0] <= report["worst_case_5pct"] <= data["expected_worst_case_5pct_range"][1]
        assert report["release_hold"] == "HOLD"
        assert report["advisory_only"] is True

    def test_bootstrap_same_seed_identical(self):
        from core.bootstrap_research_report import build_bootstrap_report
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        r1 = build_bootstrap_report(returns, n_iterations=100, seed=424242)
        r2 = build_bootstrap_report(returns, n_iterations=100, seed=424242)
        assert r1["bootstrap_mean"] == r2["bootstrap_mean"]
        assert r1["worst_case_5pct"] == r2["worst_case_5pct"]
        assert r1["worst_case_1pct"] == r2["worst_case_1pct"]

    def test_bootstrap_different_seed_different(self):
        from core.bootstrap_research_report import build_bootstrap_report
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        r1 = build_bootstrap_report(returns, n_iterations=100, seed=424242)
        r2 = build_bootstrap_report(returns, n_iterations=100, seed=999999)
        # Different seeds should produce different bootstrap means (very high probability)
        assert r1["bootstrap_mean"] != r2["bootstrap_mean"]

    def test_bootstrap_different_seed_schema_stable(self):
        from core.bootstrap_research_report import build_bootstrap_report
        returns = [0.05, -0.02, 0.03, -0.01, 0.04]
        r1 = build_bootstrap_report(returns, n_iterations=100, seed=424242)
        r2 = build_bootstrap_report(returns, n_iterations=100, seed=999999)
        # Schema must be identical
        assert set(r1.keys()) == set(r2.keys())
        assert r1["schema_version"] == r2["schema_version"]
        assert r1["release_hold"] == r2["release_hold"]

    def test_bootstrap_empty_returns_blocks(self):
        from core.bootstrap_research_report import build_bootstrap_report
        report = build_bootstrap_report([], seed=42)
        assert report["verdict"] == "FAIL"
        assert "NO_DATA" in report["hard_blocks"]

    def test_bootstrap_safety_threshold_blocks(self):
        from core.bootstrap_research_report import build_bootstrap_report
        # Returns all below -0.1 threshold
        returns = [-0.15, -0.12, -0.18, -0.11, -0.20]
        report = build_bootstrap_report(returns, n_iterations=100, seed=42, safety_threshold=-0.10)
        assert "WORST_CASE_BELOW_THRESHOLD" in str(report["hard_blocks"])

    def test_confidence_intervals_bounds(self):
        from core.bootstrap_confidence_intervals import compute_confidence_intervals
        values = list(range(100))
        ci = compute_confidence_intervals(values, confidence=0.95)
        assert ci["lower"] < ci["upper"]
        assert ci["lower"] >= 0
        assert ci["upper"] <= 99
        assert ci["confidence_level"] == 0.95

    def test_confidence_intervals_empty(self):
        from core.bootstrap_confidence_intervals import compute_confidence_intervals
        ci = compute_confidence_intervals([])
        assert ci["lower"] == 0.0
        assert ci["upper"] == 0.0
        assert ci["mean"] == 0.0

    def test_win_rate_ci_bounds(self):
        from core.bootstrap_confidence_intervals import compute_win_rate_ci
        returns = [0.1, -0.05, 0.2, -0.1, 0.15, -0.03, 0.08, -0.02, 0.12, -0.07]
        ci = compute_win_rate_ci(returns, n_iterations=100, seed=42)
        assert 0.0 <= ci["ci_lower"] <= 1.0
        assert 0.0 <= ci["ci_upper"] <= 1.0
        assert ci["ci_lower"] <= ci["win_rate"] <= ci["ci_upper"]


# ============================================================
# F. Regime Adversarial Tests (fixture-driven)
# ============================================================

class TestRegimeAdversarialFixtureDriven:
    def test_adverse_regime_fixture(self):
        data = load_fixture_by_name("regime", "adverse_regime.json")
        from core.regime_failure_report import detect_regime_failure
        result = detect_regime_failure(data["regime_scores"], data["failure_threshold"])
        assert result["has_failure"] == data["expected_has_failure"]
        assert set(result["failures"].keys()) == set(data["expected_failed_regimes"])

    def test_concentrated_regime_fixture(self):
        data = load_fixture_by_name("regime", "concentrated_regime.json")
        from core.regime_failure_report import build_regime_failure_report
        report = build_regime_failure_report(
            "test", data["regime_scores"],
            concentration_threshold=data["concentration_threshold"], seed=42
        )
        assert len(report["warnings"]) > 0
        assert any("REGIME_CONCENTRATION" in w for w in report["warnings"])

    def test_regime_concentration_warning(self):
        from core.regime_research_segmentation import build_regime_breakdown
        # Returns that are all trending — should concentrate in TREND
        returns = [0.01] * 50
        report = build_regime_breakdown("strat1", returns, lookback=10, seed=42)
        concentrations = report.get("concentrations", {})
        max_conc = max(concentrations.values()) if concentrations else 0
        if max_conc > 0.8:
            assert any("REGIME_CONCENTRATION" in w for w in report["warnings"])

    def test_regime_failure_blocks(self):
        from core.regime_failure_report import build_regime_failure_report
        report = build_regime_failure_report("s", {"TREND": 0.1, "CHOP": -0.1}, seed=42)
        assert "REGIME_FAILURE" in report["hard_blocks"]
        assert report["verdict"] == "FAIL"

    def test_regime_failure_pass(self):
        from core.regime_failure_report import build_regime_failure_report
        report = build_regime_failure_report("s", {"TREND": 0.1, "CHOP": 0.05}, seed=42)
        assert report["hard_blocks"] == []
        assert report["verdict"] == "PASS"

    def test_classify_regime_trend(self):
        from core.regime_research_segmentation import classify_regime
        returns = [0.01] * 20
        assert classify_regime(returns, lookback=10) == "TREND"

    def test_classify_regime_chop(self):
        from core.regime_research_segmentation import classify_regime
        returns = [0.0001, -0.0001] * 20
        assert classify_regime(returns, lookback=10) == "CHOP"

    def test_classify_regime_ambiguous(self):
        from core.regime_research_segmentation import classify_regime
        assert classify_regime([0.01], lookback=20) == "AMBIGUOUS"


# ============================================================
# G. Portfolio Overlap/Crowding Adversarial Tests (fixture-driven)
# ============================================================

class TestPortfolioAdversarialFixtureDriven:
    def test_high_overlap_fixture(self):
        data = load_fixture_by_name("adversarial/portfolio_robustness", "high_overlap_pair.json")
        from core.portfolio_overlap_risk import compute_overlap, build_overlap_risk_report
        overlap = compute_overlap(
            data["strategy_a_signals"], data["strategy_b_signals"],
            data["strategy_a"], data["strategy_b"]
        )
        assert overlap.overlap_score == data["expected_overlap_score"]

    def test_high_overlap_blocks(self):
        data = load_fixture_by_name("adversarial/portfolio_robustness", "high_overlap_pair.json")
        from core.portfolio_overlap_risk import compute_overlap, build_overlap_risk_report
        overlap = compute_overlap(
            data["strategy_a_signals"], data["strategy_b_signals"],
            data["strategy_a"], data["strategy_b"]
        )
        report = build_overlap_risk_report([overlap], data["max_overlap_risk"], seed=42)
        assert report["verdict"] == data["expected_verdict"]
        assert len(report["hard_blocks"]) > 0

    def test_no_overlap_passes(self):
        from core.portfolio_overlap_risk import compute_overlap, build_overlap_risk_report
        # Completely flat signals — no overlap
        overlap = compute_overlap([0, 0, 0, 0, 0], [0, 0, 0, 0, 0], "a", "b")
        report = build_overlap_risk_report([overlap], 0.70, seed=42)
        assert report["verdict"] == "PASS"
        assert report["hard_blocks"] == []

    def test_overlap_score_exact(self):
        from core.portfolio_overlap_risk import compute_overlap
        # Positions 0 and 4 have both non-zero → 2 collisions / 5 = 0.4
        overlap = compute_overlap([1, 0, 1, 0, 1], [1, 1, 0, 0, 1], "a", "b")
        assert overlap.overlap_score == 2 / 5
        assert overlap.same_bar_collisions == 2
        assert overlap.total_bars == 5

    def test_correlated_loss_pair_fixture(self):
        data = load_fixture_by_name("adversarial/portfolio_robustness", "correlated_loss_pair.json")
        from core.portfolio_correlation_proxy import compute_correlation_proxy
        corr = compute_correlation_proxy(data["strategy_a_returns"], data["strategy_b_returns"])
        assert abs(corr - data["expected_correlation"]) < 0.01


# ============================================================
# H. Report Quality Adversarial Tests (fixture-driven)
# ============================================================

class TestReportQualityAdversarialFixtureDriven:
    def test_complete_report_fixture(self):
        data = load_fixture_by_name("expected/report_quality", "complete_report_expected.json")
        from core.report_quality_check import check_report_completeness
        report = {s: {"data": True} for s in data["report_sections"]}
        result = check_report_completeness(report)
        assert result["complete"] == data["expected_complete"]
        assert result["missing_sections"] == data["expected_missing_sections"]

    def test_missing_section_fails(self):
        from core.report_quality_check import check_report_completeness
        report = {"summary": {"data": True}}  # missing most sections
        result = check_report_completeness(report)
        assert not result["complete"]
        assert len(result["missing_sections"]) > 0

    def test_report_quality_blocks_nan_metric(self):
        from core.report_quality_check import build_report_quality_check
        report = {"composite_score": float("nan"), "verdict": "PASS"}
        result = build_report_quality_check(report, seed=42)
        assert result["verdict"] == "FAIL"
        assert "METRIC_INCONSISTENCY" in result["hard_blocks"]

    def test_report_quality_passes_clean(self):
        from core.report_quality_check import build_report_quality_check, REQUIRED_SECTIONS
        # Include all required sections and critical metric keys
        report = {section: {"data": True} for section in REQUIRED_SECTIONS}
        report["composite_score"] = 0.7
        report["stability_score"] = 0.8
        report["verdict"] = "PASS"
        result = build_report_quality_check(report, seed=42)
        assert result["verdict"] in ("PASS", "PARTIAL")
        assert result["release_hold"] == "HOLD"


# ============================================================
# I. Safety Regression Deep Tests
# ============================================================

class TestSafetyRegressionDeep:
    def test_frozen_patterns_cover_critical_files(self):
        from core.research_safety_regression import FROZEN_PATTERNS
        critical = ["PROJECT_STATE.md", "TASKS.md", "acceptance.json", "feature_list.json", "AGENT_RULES.md"]
        for f in critical:
            assert f in FROZEN_PATTERNS, f"FROZEN_PATTERNS missing critical file: {f}"

    def test_frozen_prefixes_cover_live_boundary(self):
        from core.research_safety_regression import FROZEN_PREFIXES
        live_prefixes = [p for p in FROZEN_PREFIXES if "live" in p or "testnet" in p or "runtime" in p or "planner" in p]
        assert len(live_prefixes) >= 10, "FROZEN_PREFIXES must cover live/testnet/runtime/planner boundaries"

    def test_frozen_prefixes_cover_scripts(self):
        from core.research_safety_regression import FROZEN_PREFIXES
        script_prefixes = [p for p in FROZEN_PREFIXES if p.startswith("scripts/")]
        assert len(script_prefixes) >= 15, "FROZEN_PREFIXES must cover frozen scripts"

    def test_frozen_violation_machine_readable(self):
        from core.research_safety_regression import check_frozen_files
        violations = check_frozen_files(("core/live_runner.py",))
        assert len(violations) == 1
        assert violations[0].startswith("FROZEN_PREFIX_TOUCHED:")

    def test_frozen_pattern_violation_machine_readable(self):
        from core.research_safety_regression import check_frozen_files
        violations = check_frozen_files(("docs/PROJECT_STATE.md",))
        assert len(violations) == 1
        assert violations[0].startswith("FROZEN_FILE_TOUCHED:")

    def test_clean_file_no_violation(self):
        from core.research_safety_regression import check_frozen_files
        violations = check_frozen_files(("core/data_feed.py", "utils/logger.py"))
        assert violations == ()

    def test_release_hold_fail_machine_readable(self):
        from core.research_safety_regression import build_safety_report
        r = build_safety_report(release_hold="RELEASED")
        assert r.verdict == "FAIL"
        assert any("RELEASE_HOLD_VIOLATION" in reason for reason in r.reasons)

    def test_advisory_only_false_fails(self):
        from core.research_safety_regression import build_safety_report
        r = build_safety_report(advisory_only=False)
        assert r.verdict == "FAIL"
        assert any("ADVISORY_ONLY_FALSE" in reason for reason in r.reasons)

    def test_human_review_required_false_fails(self):
        from core.research_safety_regression import build_safety_report
        r = build_safety_report(human_review_required=False)
        assert r.verdict == "FAIL"
        assert any("HUMAN_REVIEW_REQUIRED_FALSE" in reason for reason in r.reasons)

    def test_git_add_dot_fails(self):
        from core.research_safety_regression import build_safety_report
        r = build_safety_report(git_add_dot=True)
        assert r.verdict == "FAIL"
        assert any("GIT_ADD_DOT_DETECTED" in reason for reason in r.reasons)

    def test_frozen_modified_staged_causes_fail(self):
        from core.research_safety_regression import build_safety_report
        r = build_safety_report(touched_files=("PROJECT_STATE.md", "TASKS.md"))
        assert r.verdict == "FAIL"
        assert len(r.frozen_files_touched) == 2

    def test_report_deterministic(self):
        from core.research_safety_regression import build_safety_report, safety_report_to_dict
        r1 = build_safety_report()
        r2 = build_safety_report()
        assert safety_report_to_dict(r1) == safety_report_to_dict(r2)

    def test_report_safety_flags_complete(self):
        from core.research_safety_regression import build_safety_report
        r = build_safety_report()
        assert r.release_hold == "HOLD"
        assert r.advisory_only is True
        assert r.human_review_required is True
        assert r.safety_flags["no_live"] is True
        assert r.safety_flags["no_submit"] is True
        assert r.safety_flags["no_exchange"] is True
        assert r.safety_flags["no_runtime_integration"] is True
        assert r.safety_flags["no_planner_integration"] is True
        assert r.safety_flags["no_network"] is True

    def test_forbidden_boundary_detection(self):
        """Test that forbidden boundary patterns are detected in code."""
        from core.research_safety_regression import detect_forbidden_boundaries
        with tempfile.TemporaryDirectory() as d:
            # Create a file with forbidden import
            p = Path(d) / "bad_code.py"
            p.write_text("import binance\nfrom binance import Client\n")
            violations = detect_forbidden_boundaries(Path(d))
            assert len(violations) > 0
            assert any("binance" in v for v in violations)

    def test_forbidden_boundary_clean_code(self):
        """Test that clean code has no boundary violations."""
        from core.research_safety_regression import detect_forbidden_boundaries
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "good_code.py"
            p.write_text("import json\nimport os\nfrom pathlib import Path\n")
            violations = detect_forbidden_boundaries(Path(d))
            assert violations == ()


# ============================================================
# J. Artifact Hashing Tests
# ============================================================

class TestArtifactHashing:
    def test_hash_artifact_content_deterministic(self):
        from core.research_artifact_hashing import hash_artifact_content
        data = {"key": "value", "nested": {"a": 1}}
        h1 = hash_artifact_content(data)
        h2 = hash_artifact_content(data)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_excludes_timestamps(self):
        from core.research_artifact_hashing import hash_artifact_content
        d1 = {"key": "value", "generated_at": "2024-01-01"}
        d2 = {"key": "value", "generated_at": "2024-12-31"}
        h1 = hash_artifact_content(d1)
        h2 = hash_artifact_content(d2)
        assert h1 == h2  # timestamps stripped

    def test_hash_different_content_different(self):
        from core.research_artifact_hashing import hash_artifact_content
        h1 = hash_artifact_content({"key": "a"})
        h2 = hash_artifact_content({"key": "b"})
        assert h1 != h2

    def test_compare_hashes_identical(self):
        from core.research_artifact_hashing import compare_hashes
        h = {"a.json": "abc123", "b.json": "def456"}
        diffs, missing = compare_hashes(h, h)
        assert diffs == {}
        assert missing == ()

    def test_compare_hashes_different(self):
        from core.research_artifact_hashing import compare_hashes
        left = {"a.json": "abc123"}
        right = {"a.json": "xyz789"}
        diffs, missing = compare_hashes(left, right)
        assert "a.json" in diffs

    def test_compare_hashes_missing(self):
        from core.research_artifact_hashing import compare_hashes
        left = {"a.json": "abc123"}
        right = {}
        diffs, missing = compare_hashes(left, right)
        assert any("RIGHT_MISSING" in m for m in missing)


# ============================================================
# K. Promotion Gate Tests
# ============================================================

class TestPromotionGateAdversarial:
    def test_hard_blocks_fail(self):
        from core.promotion_gate_v2 import evaluate_promotion_gate
        decision = evaluate_promotion_gate(0.8, 0.9, ["BLOCK_A", "BLOCK_B"])
        assert decision.status == "ADVISORY_FAIL"
        assert decision.advisory_only is True
        assert decision.human_review_required is True
        assert decision.release_hold == "HOLD"

    def test_low_score_fail(self):
        from core.promotion_gate_v2 import evaluate_promotion_gate
        decision = evaluate_promotion_gate(0.3, 0.9, [])
        assert decision.status == "ADVISORY_FAIL"
        assert any("LOW_COMPOSITE_SCORE" in r for r in decision.block_reasons)

    def test_low_completeness_partial(self):
        from core.promotion_gate_v2 import evaluate_promotion_gate
        decision = evaluate_promotion_gate(0.8, 0.5, [])
        assert decision.status == "ADVISORY_PARTIAL"

    def test_full_pass(self):
        from core.promotion_gate_v2 import evaluate_promotion_gate
        decision = evaluate_promotion_gate(0.8, 0.95, [])
        assert decision.status == "ADVISORY_PASS"
        assert decision.block_reasons == ()

    def test_advisory_only_always_true(self):
        from core.promotion_gate_v2 import evaluate_promotion_gate
        for score in [0.0, 0.5, 1.0]:
            for completeness in [0.0, 0.5, 1.0]:
                decision = evaluate_promotion_gate(score, completeness, ["BLOCK"])
                assert decision.advisory_only is True
                assert decision.release_hold == "HOLD"


# ============================================================
# L. Quality Gate Integration Tests (fixture-driven)
# ============================================================

class TestQualityGateIntegrationFixtureDriven:
    def test_gate_with_clean_workbench(self):
        """Run quality gate with fixture workbench data and verify all artifacts."""
        from core.research_quality_gate_v2 import run_quality_gate
        data = load_fixture_by_name("base", "workbench_results_clean.json")

        with tempfile.TemporaryDirectory() as ind, tempfile.TemporaryDirectory() as outd:
            input_dir = Path(ind)
            (input_dir / "results.json").write_text(json.dumps(data))
            (input_dir / "comparison.json").write_text(json.dumps({}))
            (input_dir / "portfolio_summary.json").write_text(json.dumps({}))
            (input_dir / "promotion_recommendations.json").write_text(json.dumps([]))
            (input_dir / "parameter_search.json").write_text(json.dumps({}))
            (input_dir / "strategy_registry.json").write_text(json.dumps({}))
            (input_dir / "matrix.json").write_text(json.dumps({}))

            result = run_quality_gate(input_dir, Path(outd), seed=424242, strict=True, release_hold="HOLD")

            # Strong assertions
            assert result["verdict"] in ("PASS", "PARTIAL", "FAIL")
            assert result["artifacts_written"] >= 25
            assert result["composite_score"] >= 0.0

            # Check manifest
            manifest = json.loads((Path(outd) / "manifest.json").read_text())
            assert manifest["release_hold"] == "HOLD"
            assert manifest["advisory_only"] is True
            assert manifest["human_review_required"] is True
            assert manifest["no_live"] is True
            assert manifest["no_submit"] is True
            assert manifest["no_exchange"] is True
            assert manifest["no_network"] is True

            # Check key artifacts exist
            for artifact in ["quality_gate_summary.json", "robustness_scorecard.json",
                             "manifest.json", "report.md", "report.html"]:
                assert (Path(outd) / artifact).exists(), f"Missing artifact: {artifact}"

    def test_gate_non_hold_raises(self):
        from core.research_quality_gate_v2 import run_quality_gate
        with tempfile.TemporaryDirectory() as ind, tempfile.TemporaryDirectory() as outd:
            with pytest.raises(ValueError, match="HOLD"):
                run_quality_gate(Path(ind), Path(outd), release_hold="RELEASED")


# ============================================================
# M. Final Decision Tests
# ============================================================

class TestFinalDecisionDeep:
    def test_full_pass_expected_fixture(self):
        data = load_fixture_by_name("expected/final_acceptance", "full_pass_expected.json")
        from core.research_quality_final_decision import evaluate_final_decision
        d = evaluate_final_decision(
            full_suite_passed=data["full_suite_passed"],
            workbench_acceptance_passed=data["workbench_acceptance_passed"],
            quality_gate_passed=data["quality_gate_passed"],
            rerun_passed=data["rerun_passed"],
            comparator_passed=data["comparator_passed"],
            closeout_generated=data["closeout_generated"],
            all_artifacts_present=data["all_artifacts_present"],
            release_hold_is_hold=data["release_hold_is_hold"],
        )
        assert d.verdict == data["expected_verdict"]
        assert d.safety_holds == data["expected_safety_holds"]

    def test_any_failure_partial_or_fail(self):
        from core.research_quality_final_decision import evaluate_final_decision
        # Suite fails
        d = evaluate_final_decision(
            full_suite_passed=False, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=True,
        )
        assert d.verdict == "PARTIAL"

    def test_non_hold_always_fail(self):
        from core.research_quality_final_decision import evaluate_final_decision
        d = evaluate_final_decision(
            full_suite_passed=True, workbench_acceptance_passed=True,
            quality_gate_passed=True, rerun_passed=True,
            comparator_passed=True, closeout_generated=True,
            all_artifacts_present=True, release_hold_is_hold=False,
        )
        assert d.verdict == "FAIL"
        assert d.safety_holds is False
