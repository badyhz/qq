"""Verify offline shadow research pipeline integrity.

Runs all tests, checks module imports, validates fixtures, runs
pipeline end-to-end, and verifies output artifacts.

Usage:
    python3 scripts/verify_offline_shadow_research_pipeline.py
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURE_DIR = str(_REPO_ROOT / "tests" / "fixtures" / "offline_shadow_research")

# All modules that must be importable
_REQUIRED_MODULES = [
    "core.offline_shadow_safety_policy",
    "core.offline_shadow_symbol",
    "core.offline_shadow_timeframe",
    "core.offline_shadow_window",
    "core.offline_shadow_parameter_set",
    "core.offline_shadow_experiment",
    "core.offline_shadow_run_config",
    "core.offline_shadow_experiment_plan",
    "core.offline_shadow_fixture_loader",
    "core.offline_shadow_plan_generator",
    "core.offline_shadow_matrix_materializer",
    "core.offline_shadow_metric_engine",
    "core.offline_shadow_evaluator",
    "core.offline_shadow_scorecard",
    "core.offline_shadow_comparison",
    "core.offline_shadow_report_renderer",
    "core.offline_shadow_bundle_builder",
    "core.offline_shadow_recommendation_engine",
]

_REQUIRED_SCRIPTS = [
    "scripts.run_offline_shadow_research_pipeline",
    "scripts.build_offline_shadow_research_bundle",
]

_TEST_FILES = [
    "tests/unit/test_offline_shadow_negative.py",
    "tests/unit/test_offline_shadow_recommendation_engine.py",
    "tests/unit/test_offline_shadow_acceptance.py",
]


def _check_imports() -> list[str]:
    """Check all required modules are importable."""
    errors: list[str] = []
    for mod_name in _REQUIRED_MODULES + _REQUIRED_SCRIPTS:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            errors.append(f"  FAIL {mod_name}: {e}")
    return errors


def _check_fixtures() -> list[str]:
    """Validate fixture files exist and load correctly."""
    errors: list[str] = []
    fixture_path = Path(FIXTURE_DIR)
    if not fixture_path.exists():
        errors.append(f"  FAIL fixture dir missing: {FIXTURE_DIR}")
        return errors

    from core.offline_shadow_fixture_loader import load_fixtures, validate_fixture

    try:
        fixtures = load_fixtures(FIXTURE_DIR)
    except Exception as e:
        errors.append(f"  FAIL load_fixtures: {e}")
        return errors

    if not fixtures:
        errors.append("  FAIL no experiment fixtures found")
        return errors

    for f in fixtures:
        if not validate_fixture(f):
            errors.append(f"  FAIL invalid fixture: {f.get('experiment_id', '?')}")

    return errors


def _check_pipeline_e2e() -> list[str]:
    """Run the pipeline end-to-end with fixtures."""
    errors: list[str] = []

    from core.offline_shadow_bundle_builder import build_bundle, compute_sha256
    from core.offline_shadow_metric_engine import compute_run_metrics
    from core.offline_shadow_plan_generator import generate_experiment_plan
    from core.offline_shadow_recommendation_engine import generate_recommendations
    from core.offline_shadow_report_renderer import render_report_json, render_report_markdown
    from core.offline_shadow_run_config import OfflineShadowRunConfig
    from core.offline_shadow_scorecard import grade_run

    rc = OfflineShadowRunConfig(
        config_id="verify_run",
        symbols=("BTCUSDT",),
        timeframes=("5m",),
        windows=("train",),
        param_grid=("conservative",),
        fixture_dir=FIXTURE_DIR,
        output_dir="/tmp/verify_output",
    )

    try:
        plan = generate_experiment_plan(rc)
    except Exception as e:
        errors.append(f"  FAIL generate_experiment_plan: {e}")
        return errors

    if plan.safety_policy.release_hold != "HOLD":
        errors.append("  FAIL safety_policy.release_hold != HOLD")
        return errors

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

    recs = generate_recommendations(
        [{"experiment_id": r["experiment_id"], **r["metrics"]} for r in results]
    )

    report_md = render_report_markdown(results)
    report_json_data = render_report_json(results)

    if report_json_data.get("release_hold") != "HOLD":
        errors.append("  FAIL json report missing release_hold=HOLD")

    if not recs:
        errors.append("  FAIL no recommendations generated")

    # Build bundle
    bundle = build_bundle(
        plan_data={"plan_id": plan.plan_id},
        matrix_data={"runs": []},
        results_data=results,
        scorecard_data={},
        report_markdown=report_md,
        report_html="",
        report_json=report_json_data,
    )

    if "manifest.json" not in bundle:
        errors.append("  FAIL manifest.json missing from bundle")
    else:
        manifest = json.loads(bundle["manifest.json"])
        if manifest.get("release_hold") != "HOLD":
            errors.append("  FAIL manifest missing release_hold=HOLD")

    return errors


def _run_tests() -> tuple[bool, str]:
    """Run all offline shadow test files."""
    test_paths = [str(_REPO_ROOT / t) for t in _TEST_FILES]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *test_paths, "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return result.returncode == 0, result.stdout + result.stderr


def main() -> int:
    print("=" * 60)
    print("OFFLINE SHADOW RESEARCH PIPELINE VERIFICATION")
    print("=" * 60)

    all_ok = True

    # 1. Module imports
    print("\n[1/5] Checking module imports...")
    import_errors = _check_imports()
    if import_errors:
        all_ok = False
        for e in import_errors:
            print(e)
    else:
        print("  OK - all modules importable")

    # 2. Fixture integrity
    print("\n[2/5] Validating fixtures...")
    fixture_errors = _check_fixtures()
    if fixture_errors:
        all_ok = False
        for e in fixture_errors:
            print(e)
    else:
        print("  OK - fixtures valid")

    # 3. Pipeline end-to-end
    print("\n[3/5] Running pipeline end-to-end...")
    pipeline_errors = _check_pipeline_e2e()
    if pipeline_errors:
        all_ok = False
        for e in pipeline_errors:
            print(e)
    else:
        print("  OK - pipeline runs successfully")

    # 4. Run tests
    print("\n[4/5] Running test suite...")
    tests_ok, test_output = _run_tests()
    if not tests_ok:
        all_ok = False
        print("  FAIL - some tests failed")
        # Print last 20 lines of output
        lines = test_output.strip().split("\n")
        for line in lines[-20:]:
            print(f"  {line}")
    else:
        # Count passed
        passed = test_output.count(" PASSED")
        print(f"  OK - {passed} tests passed")

    # 5. Summary
    print("\n[5/5] Verification summary")
    print("-" * 60)
    if all_ok:
        print("RESULT: PASS")
        print("All checks passed. release_hold=HOLD")
        return 0
    else:
        print("RESULT: FAIL")
        print("Some checks failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
