"""Tests for offline shadow pipeline orchestrator (Phase 11)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURE_DIR = str(_REPO_ROOT / "tests" / "fixtures" / "offline_shadow_research")


# ---------------------------------------------------------------------------
# import the orchestrator module
# ---------------------------------------------------------------------------

from scripts.run_offline_shadow_research_pipeline import (
    _evaluate_plan,
    _plan_to_dict,
    main,
)

from core.offline_shadow_plan_generator import generate_experiment_plan
from core.offline_shadow_run_config import OfflineShadowRunConfig


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_run_config(**overrides):
    defaults = dict(
        config_id="test_pipeline",
        symbols=("BTCUSDT",),
        timeframes=("5m",),
        windows=("train",),
        param_grid=("conservative",),
        fixture_dir=FIXTURE_DIR,
        output_dir="/tmp/test_pipeline",
    )
    defaults.update(overrides)
    return OfflineShadowRunConfig(**defaults)


# ---------------------------------------------------------------------------
# _plan_to_dict tests
# ---------------------------------------------------------------------------

class TestPlanToDict:
    def test_returns_dict(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        d = _plan_to_dict(plan)
        assert isinstance(d, dict)

    def test_has_plan_id(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        d = _plan_to_dict(plan)
        assert d["plan_id"] == "test_pipeline"

    def test_has_experiments(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        d = _plan_to_dict(plan)
        assert len(d["experiments"]) == 1  # 1 symbol * 1 tf * 1 window * 1 param

    def test_safety_policy_hold(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        d = _plan_to_dict(plan)
        assert d["safety_policy"]["release_hold"] == "HOLD"
        assert d["safety_policy"]["no_live"] is True

    def test_experiment_fields(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        d = _plan_to_dict(plan)
        exp = d["experiments"][0]
        assert exp["symbol"] == "BTCUSDT"
        assert exp["timeframe"] == "5m"
        assert exp["param_label"] == "conservative"


# ---------------------------------------------------------------------------
# _evaluate_plan tests
# ---------------------------------------------------------------------------

class TestEvaluatePlan:
    def test_returns_list(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        results = _evaluate_plan(plan, FIXTURE_DIR)
        assert isinstance(results, list)

    def test_result_count_matches_experiments(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        results = _evaluate_plan(plan, FIXTURE_DIR)
        assert len(results) == len(plan.experiments)

    def test_result_has_metrics(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        results = _evaluate_plan(plan, FIXTURE_DIR)
        assert "metrics" in results[0]
        assert "candidate_count" in results[0]["metrics"]

    def test_result_has_scorecard(self):
        config = _make_run_config()
        plan = generate_experiment_plan(config)
        results = _evaluate_plan(plan, FIXTURE_DIR)
        assert "scorecard" in results[0]
        assert "grade" in results[0]["scorecard"]


# ---------------------------------------------------------------------------
# main() integration tests
# ---------------------------------------------------------------------------

class TestMainIntegration:
    def test_full_pipeline(self, tmp_path):
        output_dir = str(tmp_path / "output")
        rc = main([
            "--output-dir", output_dir,
            "--fixture-dir", FIXTURE_DIR,
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        assert rc == 0

    def test_creates_all_artifacts(self, tmp_path):
        output_dir = tmp_path / "output"
        main([
            "--output-dir", str(output_dir),
            "--fixture-dir", FIXTURE_DIR,
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        required = [
            "plan.json", "matrix.json", "results.json",
            "report.md", "report.html", "scorecard.json", "manifest.json",
        ]
        for name in required:
            assert (output_dir / name).exists(), f"missing {name}"

    def test_manifest_safety(self, tmp_path):
        output_dir = tmp_path / "output"
        main([
            "--output-dir", str(output_dir),
            "--fixture-dir", FIXTURE_DIR,
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        manifest = json.loads((output_dir / "manifest.json").read_text())
        assert manifest["release_hold"] == "HOLD"
        assert manifest["no_live"] is True
        assert manifest["no_submit"] is True
        assert manifest["no_exchange"] is True

    def test_multiple_symbols(self, tmp_path):
        output_dir = tmp_path / "output"
        rc = main([
            "--output-dir", str(output_dir),
            "--fixture-dir", FIXTURE_DIR,
            "--symbols", "BTCUSDT,ETHUSDT",
            "--timeframes", "5m",
            "--param-grid", "conservative",
        ])
        assert rc == 0
        results = json.loads((output_dir / "results.json").read_text())
        symbols_in_results = {r["symbol"] for r in results}
        assert "BTCUSDT" in symbols_in_results
        assert "ETHUSDT" in symbols_in_results

    def test_invalid_timeframe(self, tmp_path):
        output_dir = str(tmp_path / "output")
        rc = main([
            "--output-dir", output_dir,
            "--fixture-dir", FIXTURE_DIR,
            "--symbols", "BTCUSDT",
            "--timeframes", "invalid_tf",
            "--param-grid", "conservative",
        ])
        assert rc == 1

    def test_invalid_param_grid(self, tmp_path):
        output_dir = str(tmp_path / "output")
        rc = main([
            "--output-dir", output_dir,
            "--fixture-dir", FIXTURE_DIR,
            "--symbols", "BTCUSDT",
            "--timeframes", "5m",
            "--param-grid", "invalid_param",
        ])
        assert rc == 1
