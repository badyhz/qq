"""Phase 17: Acceptance tests for offline shadow research pipeline.

15+ tests covering end-to-end pipeline, safety flags, manifest integrity,
report content, scorecard quality gates, recommendation engine integration,
CLI script imports, and core module imports.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURE_DIR = str(_REPO_ROOT / "tests" / "fixtures" / "offline_shadow_research")


# ---------------------------------------------------------------------------
# 1. All core modules importable
# ---------------------------------------------------------------------------

class TestCoreModulesImportable:
    def test_import_safety_policy(self):
        from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
        assert OfflineShadowSafetyPolicy is not None

    def test_import_experiment(self):
        from core.offline_shadow_experiment import OfflineShadowExperiment
        assert OfflineShadowExperiment is not None

    def test_import_experiment_plan(self):
        from core.offline_shadow_experiment_plan import OfflineShadowExperimentPlan
        assert OfflineShadowExperimentPlan is not None

    def test_import_metric_engine(self):
        from core.offline_shadow_metric_engine import compute_run_metrics, compute_aggregate_metrics
        assert compute_run_metrics is not None
        assert compute_aggregate_metrics is not None

    def test_import_recommendation_engine(self):
        from core.offline_shadow_recommendation_engine import (
            generate_recommendations, rank_recommendations, filter_recommendations,
        )
        assert generate_recommendations is not None

    def test_import_evaluator(self):
        from core.offline_shadow_evaluator import evaluate_experiment
        assert evaluate_experiment is not None

    def test_import_scorecard(self):
        from core.offline_shadow_scorecard import grade_run, grade_experiment
        assert grade_run is not None

    def test_import_comparison(self):
        from core.offline_shadow_comparison import compare_experiments
        assert compare_experiments is not None

    def test_import_report_renderer(self):
        from core.offline_shadow_report_renderer import render_report_markdown, render_report_json, render_report_html
        assert render_report_markdown is not None

    def test_import_bundle_builder(self):
        from core.offline_shadow_bundle_builder import build_manifest, compute_sha256, build_bundle
        assert build_manifest is not None

    def test_import_fixture_loader(self):
        from core.offline_shadow_fixture_loader import load_fixtures, validate_fixture, load_outcomes
        assert load_fixtures is not None

    def test_import_plan_generator(self):
        from core.offline_shadow_plan_generator import generate_experiment_plan, PARAM_GRIDS, TIMEFRAME_DEFS
        assert generate_experiment_plan is not None

    def test_import_matrix_materializer(self):
        from core.offline_shadow_matrix_materializer import materialize_replay_matrix
        assert materialize_replay_matrix is not None


# ---------------------------------------------------------------------------
# 2. CLI scripts importable
# ---------------------------------------------------------------------------

class TestCLIScriptsImportable:
    def test_pipeline_script_importable(self):
        spec = __import__(
            "scripts.run_offline_shadow_research_pipeline",
            fromlist=["main"],
        )
        assert hasattr(spec, "main")

    def test_bundle_script_importable(self):
        spec = __import__(
            "scripts.build_offline_shadow_research_bundle",
            fromlist=["main"],
        )
        assert hasattr(spec, "main")


# ---------------------------------------------------------------------------
# 3. End-to-end pipeline execution with fixtures
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    def test_full_pipeline_with_fixtures(self):
        from core.offline_shadow_bundle_builder import build_manifest, compute_sha256
        from core.offline_shadow_comparison import compare_experiments
        from core.offline_shadow_evaluator import evaluate_experiment
        from core.offline_shadow_fixture_loader import load_fixtures
        from core.offline_shadow_metric_engine import compute_run_metrics
        from core.offline_shadow_plan_generator import generate_experiment_plan
        from core.offline_shadow_recommendation_engine import generate_recommendations
        from core.offline_shadow_report_renderer import render_report_markdown, render_report_json
        from core.offline_shadow_run_config import OfflineShadowRunConfig
        from core.offline_shadow_safety_policy import OfflineShadowSafetyPolicy
        from core.offline_shadow_scorecard import grade_run

        rc = OfflineShadowRunConfig(
            config_id="acc_001",
            symbols=("BTCUSDT",),
            timeframes=("5m",),
            windows=("train",),
            param_grid=("conservative",),
            fixture_dir=FIXTURE_DIR,
            output_dir="/tmp/acc_test",
        )

        plan = generate_experiment_plan(rc)
        assert len(plan.experiments) >= 1
        assert plan.safety_policy.release_hold == "HOLD"

        outcomes = [
            {"return_r": 0.5, "mfe_r": 1.2, "mae_r": -0.3},
            {"return_r": -0.8, "mfe_r": 0.2, "mae_r": -1.0},
            {"return_r": 1.5, "mfe_r": 2.0, "mae_r": -0.1},
            {"return_r": 0.3, "mfe_r": 0.8, "mae_r": -0.5},
            {"return_r": 0.2, "mfe_r": 0.4, "mae_r": -0.2},
            {"return_r": 1.0, "mfe_r": 1.5, "mae_r": -0.1},
        ]

        results = []
        for exp in plan.experiments:
            metrics = compute_run_metrics(outcomes)
            grade_info = grade_run(metrics)
            results.append({
                "experiment_id": exp.experiment_id,
                "symbol": exp.symbol.symbol,
                "timeframe": exp.timeframe.label,
                "param_label": exp.parameter_set.label,
                "window_id": exp.window.window_id,
                "metrics": metrics,
                "scorecard": grade_info,
            })

        if len(results) >= 2:
            comparison = compare_experiments(results[0], results[1])
        else:
            comparison = compare_experiments(
                {"experiment_id": "a", "runs": []},
                {"experiment_id": "b", "runs": []},
            )
        recs = generate_recommendations(
            [{"experiment_id": r["experiment_id"], **r["metrics"]} for r in results]
        )

        assert len(results) >= 1
        assert len(recs) >= 1
        assert "deltas" in comparison

        report_md = render_report_markdown(results)
        report_json_data = render_report_json(results)
        assert "release_hold" in report_md or "HOLD" in report_md
        assert report_json_data["release_hold"] == "HOLD"


# ---------------------------------------------------------------------------
# 4. Safety flags present in output
# ---------------------------------------------------------------------------

class TestSafetyFlagsInOutput:
    def test_markdown_report_contains_safety(self):
        from core.offline_shadow_report_renderer import render_report_markdown
        sample = [{
            "experiment_id": "e1", "symbol": "BTCUSDT", "timeframe": "5m",
            "param_label": "conservative", "metrics": {"win_rate": 0.6, "expectancy_r": 0.3, "profit_factor": 1.5, "candidate_count": 10},
            "scorecard": {"grade": "PASS"},
        }]
        report = render_report_markdown(sample)
        assert "HOLD" in report

    def test_json_report_contains_safety(self):
        from core.offline_shadow_report_renderer import render_report_json
        report = render_report_json([])
        assert report["release_hold"] == "HOLD"

    def test_html_report_contains_safety(self):
        from core.offline_shadow_report_renderer import render_report_html
        report = render_report_html([])
        assert "HOLD" in report

    def test_bundle_manifest_contains_safety(self):
        from core.offline_shadow_bundle_builder import build_manifest
        manifest = build_manifest([])
        assert manifest["release_hold"] == "HOLD"
        assert manifest["no_live"] is True
        assert manifest["no_submit"] is True
        assert manifest["no_exchange"] is True


# ---------------------------------------------------------------------------
# 5. Manifest integrity
# ---------------------------------------------------------------------------

class TestManifestIntegrity:
    def test_manifest_sha256(self):
        from core.offline_shadow_bundle_builder import compute_sha256
        h = compute_sha256("hello world")
        assert len(h) == 64
        assert h == compute_sha256("hello world")  # deterministic

    def test_manifest_differs_for_different_content(self):
        from core.offline_shadow_bundle_builder import compute_sha256
        h1 = compute_sha256("content A")
        h2 = compute_sha256("content B")
        assert h1 != h2

    def test_bundle_builds_with_artifacts(self):
        from core.offline_shadow_bundle_builder import build_bundle
        bundle = build_bundle(
            plan_data={"plan_id": "test"},
            matrix_data={"runs": []},
            results_data=[],
            scorecard_data={"experiments": []},
            report_markdown="# Test",
            report_html="<h1>Test</h1>",
            report_json={"release_hold": "HOLD"},
        )
        assert "manifest.json" in bundle
        manifest = json.loads(bundle["manifest.json"])
        assert manifest["release_hold"] == "HOLD"
        assert manifest["artifact_count"] > 0


# ---------------------------------------------------------------------------
# 6. Scorecard quality gates
# ---------------------------------------------------------------------------

class TestScorecardQualityGates:
    def test_good_metrics_get_pass_grade(self):
        from core.offline_shadow_scorecard import grade_run
        metrics = {
            "candidate_count": 20,
            "win_rate": 0.65,
            "expectancy_r": 0.5,
            "sample_quality_score": 0.7,
            "max_drawdown_r": -2.0,
        }
        result = grade_run(metrics)
        assert result["grade"] in ("PASS", "WATCH")

    def test_bad_metrics_get_reject_grade(self):
        from core.offline_shadow_scorecard import grade_run
        metrics = {
            "candidate_count": 2,
            "win_rate": 0.1,
            "expectancy_r": -2.0,
            "sample_quality_score": 0.1,
            "max_drawdown_r": -10.0,
        }
        result = grade_run(metrics)
        assert result["grade"] == "REJECT"
        assert len(result["blockers"]) > 0

    def test_evaluator_with_matrix(self):
        from core.offline_shadow_evaluator import evaluate_experiment
        matrix = {
            "experiment_id": "test_exp",
            "runs": [{"run_id": "outcomes_BTCUSDT_5m"}],
        }
        result = evaluate_experiment(matrix, FIXTURE_DIR)
        assert result["experiment_id"] == "test_exp"
        assert result["run_count"] >= 1
        assert "metrics" in result["runs"][0]


# ---------------------------------------------------------------------------
# 7. Recommendation engine integration
# ---------------------------------------------------------------------------

class TestRecommendationIntegration:
    def test_recommendations_from_pipeline_results(self):
        from core.offline_shadow_recommendation_engine import generate_recommendations, rank_recommendations
        results = [
            {"experiment_id": "e1", "expectancy_r": 0.5, "win_rate": 0.62, "sample_quality_score": 0.7, "max_drawdown_r": -2.0},
            {"experiment_id": "e2", "expectancy_r": -0.5, "win_rate": 0.3, "sample_quality_score": 0.2, "max_drawdown_r": -8.0},
        ]
        recs = generate_recommendations(results)
        ranked = rank_recommendations(recs)
        assert len(ranked) == 2
        assert ranked[0].action == "DEPLOY"
        assert ranked[1].action == "REJECT"

    def test_recommendations_have_risk_factors(self):
        from core.offline_shadow_recommendation_engine import generate_recommendations
        results = [
            {"experiment_id": "e1", "expectancy_r": -1.0, "win_rate": 0.2, "sample_quality_score": 0.1, "max_drawdown_r": -15.0},
        ]
        recs = generate_recommendations(results)
        assert len(recs[0].risk_factors) > 0


# ---------------------------------------------------------------------------
# 8. Fixture integrity
# ---------------------------------------------------------------------------

class TestFixtureIntegrity:
    def test_fixtures_load(self):
        from core.offline_shadow_fixture_loader import load_fixtures
        fixtures = load_fixtures(FIXTURE_DIR)
        assert len(fixtures) >= 1

    def test_fixtures_have_required_fields(self):
        from core.offline_shadow_fixture_loader import load_fixtures, validate_fixture
        fixtures = load_fixtures(FIXTURE_DIR)
        for f in fixtures:
            assert validate_fixture(f), f"Missing required fields in {f.get('experiment_id', '?')}"

    def test_fixtures_have_experiment_ids(self):
        from core.offline_shadow_fixture_loader import load_fixtures
        fixtures = load_fixtures(FIXTURE_DIR)
        ids = [f["experiment_id"] for f in fixtures]
        assert len(ids) == len(set(ids))  # no duplicates
