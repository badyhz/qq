"""Golden fixture regression tests (Phase 12).

Compares actual function outputs against stored expected JSON files.
Any change to core logic will be caught by these tests.
"""
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURE_DIR = str(_REPO_ROOT / "tests" / "fixtures" / "offline_shadow_research")
EXPECTED_DIR = str(_REPO_ROOT / "tests" / "fixtures" / "offline_shadow_research" / "expected")

from core.offline_shadow_bundle_builder import build_manifest, compute_sha256
from core.offline_shadow_fixture_loader import load_outcomes
from core.offline_shadow_metric_engine import compute_aggregate_metrics, compute_run_metrics
from core.offline_shadow_plan_generator import generate_experiment_plan
from core.offline_shadow_report_renderer import render_report_json
from core.offline_shadow_run_config import OfflineShadowRunConfig
from core.offline_shadow_scorecard import grade_run


def _load_expected(name: str) -> dict:
    path = Path(EXPECTED_DIR) / name
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# golden fixture tests
# ---------------------------------------------------------------------------

class TestGoldenRunMetrics:
    def test_run_metrics_sample(self):
        outcomes = [
            {"return_r": 0.5, "mfe_r": 0.6, "mae_r": -0.1},
            {"return_r": -0.2, "mfe_r": 0.1, "mae_r": -0.3},
            {"return_r": 1.0, "mfe_r": 1.2, "mae_r": -0.05},
            {"return_r": 0.3, "mfe_r": 0.4, "mae_r": -0.08},
            {"return_r": -0.1, "mfe_r": 0.05, "mae_r": -0.15},
        ]
        actual = compute_run_metrics(outcomes)
        expected = _load_expected("run_metrics_sample.json")
        assert actual == expected

    def test_run_metrics_empty(self):
        actual = compute_run_metrics([])
        expected = _load_expected("run_metrics_empty.json")
        assert actual == expected


class TestGoldenAggregateMetrics:
    def test_aggregate_metrics_sample(self):
        outcomes = [
            {"return_r": 0.5, "mfe_r": 0.6, "mae_r": -0.1},
            {"return_r": -0.2, "mfe_r": 0.1, "mae_r": -0.3},
            {"return_r": 1.0, "mfe_r": 1.2, "mae_r": -0.05},
            {"return_r": 0.3, "mfe_r": 0.4, "mae_r": -0.08},
            {"return_r": -0.1, "mfe_r": 0.05, "mae_r": -0.15},
        ]
        metrics = compute_run_metrics(outcomes)
        actual = compute_aggregate_metrics([metrics, metrics])
        expected = _load_expected("aggregate_metrics_sample.json")
        assert actual == expected


class TestGoldenGradeRun:
    def test_grade_run_good(self):
        outcomes = [
            {"return_r": 0.5, "mfe_r": 0.6, "mae_r": -0.1},
            {"return_r": -0.2, "mfe_r": 0.1, "mae_r": -0.3},
            {"return_r": 1.0, "mfe_r": 1.2, "mae_r": -0.05},
            {"return_r": 0.3, "mfe_r": 0.4, "mae_r": -0.08},
            {"return_r": -0.1, "mfe_r": 0.05, "mae_r": -0.15},
        ]
        metrics = compute_run_metrics(outcomes)
        actual = grade_run(metrics)
        expected = _load_expected("grade_run_good.json")
        assert actual == expected

    def test_grade_run_bad(self):
        bad_outcomes = [
            {"return_r": -0.5, "mfe_r": 0.1, "mae_r": -0.6},
            {"return_r": -0.3, "mfe_r": 0.05, "mae_r": -0.4},
        ]
        metrics = compute_run_metrics(bad_outcomes)
        actual = grade_run(metrics)
        expected = _load_expected("grade_run_bad.json")
        assert actual == expected


class TestGoldenReportJson:
    def test_report_json_sample(self):
        outcomes = [
            {"return_r": 0.5, "mfe_r": 0.6, "mae_r": -0.1},
            {"return_r": -0.2, "mfe_r": 0.1, "mae_r": -0.3},
            {"return_r": 1.0, "mfe_r": 1.2, "mae_r": -0.05},
            {"return_r": 0.3, "mfe_r": 0.4, "mae_r": -0.08},
            {"return_r": -0.1, "mfe_r": 0.05, "mae_r": -0.15},
        ]
        metrics = compute_run_metrics(outcomes)
        grade = grade_run(metrics)
        results = [
            {
                "experiment_id": "exp_0000",
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "param_label": "conservative",
                "window_id": "w_train",
                "metrics": metrics,
                "scorecard": grade,
            }
        ]
        actual = render_report_json(results)
        expected = _load_expected("report_json_sample.json")
        assert actual == expected


class TestGoldenSha256:
    def test_sha256_hello(self):
        actual = compute_sha256("hello")
        expected = _load_expected("sha256_hello.json")
        assert actual == expected["sha256"]


class TestGoldenManifest:
    def test_manifest_sample(self):
        actual = build_manifest([{"name": "a.json", "sha256": "abc123"}])
        expected = _load_expected("manifest_sample.json")
        assert actual == expected


class TestGoldenPlanGeneration:
    def test_plan_generation_sample(self):
        config = OfflineShadowRunConfig(
            config_id="golden_test",
            symbols=("BTCUSDT",),
            timeframes=("5m",),
            windows=("train",),
            param_grid=("conservative",),
            fixture_dir=FIXTURE_DIR,
            output_dir="/tmp/golden",
        )
        plan = generate_experiment_plan(config)
        expected = _load_expected("plan_generation_sample.json")
        assert plan.plan_id == expected["plan_id"]
        assert len(plan.experiments) == expected["experiment_count"]
        assert plan.experiments[0].experiment_id == expected["first_experiment_id"]
        assert plan.safety_policy.release_hold == expected["safety_policy"]["release_hold"]
        assert plan.safety_policy.no_live == expected["safety_policy"]["no_live"]


class TestGoldenActualFixtures:
    def test_metrics_btcusdt_5m(self):
        outcomes = load_outcomes(FIXTURE_DIR, "BTCUSDT", "5m")
        actual = compute_run_metrics(outcomes)
        expected = _load_expected("metrics_btcusdt_5m.json")
        assert actual == expected

    def test_metrics_deterministic(self):
        """Running the same computation twice must yield identical results."""
        outcomes = load_outcomes(FIXTURE_DIR, "BTCUSDT", "5m")
        r1 = compute_run_metrics(outcomes)
        r2 = compute_run_metrics(outcomes)
        assert r1 == r2
