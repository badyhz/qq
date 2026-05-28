"""Tests for research artifact browser CLI and comparison — T9361-T9800.

CLI creates all artifacts. Deterministic rerun. Compare identical PASS.
Compare changed hash. Compare safety flag mismatch FAIL.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from core.research_artifact_browser import (
    build_artifact_browser_index,
    build_review_model,
    validate_artifact_schema,
    artifact_browser_index_to_dict,
    review_model_to_dict,
    schema_validation_to_dict,
)
from core.research_artifact_compare import (
    compare_browser_outputs,
    comparison_to_dict,
    comparison_to_json,
    comparison_to_markdown,
)
from core.research_static_report_renderer import (
    render_html_report,
    render_markdown_report,
    render_human_review_checklist,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_artifact_browser"
SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"


EXPECTED_BROWSER_ARTIFACTS = [
    "artifact_browser_index.json",
    "artifact_schema_validation.json",
    "review_model.json",
    "artifact_browser.html",
    "artifact_browser.md",
    "human_review_checklist.json",
    "human_review_checklist.md",
    "artifact_browser_manifest.json",
]


class TestBrowserCliCreatesAllArtifacts:
    def test_cli_creates_all_expected_artifacts(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                 "--quality-dir", str(FIXTURES / "quality_bundle_pass"),
                 "--output-dir", out, "--strict", "--release-hold", "HOLD"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"stderr: {result.stderr}"
            outpath = Path(out)
            for name in EXPECTED_BROWSER_ARTIFACTS:
                assert (outpath / name).exists(), f"Missing: {name}"

    def test_cli_pass_output(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                 "--quality-dir", str(FIXTURES / "quality_bundle_pass"),
                 "--output-dir", out, "--strict", "--release-hold", "HOLD"],
                capture_output=True, text=True,
            )
            assert "PASS" in result.stdout

    def test_cli_fails_on_missing_quality_dir(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                 "--quality-dir", "/nonexistent",
                 "--output-dir", out, "--strict", "--release-hold", "HOLD"],
                capture_output=True, text=True,
            )
            assert result.returncode != 0

    def test_cli_fails_on_non_hold(self):
        with tempfile.TemporaryDirectory() as out:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                 "--quality-dir", str(FIXTURES / "quality_bundle_pass"),
                 "--output-dir", out, "--strict", "--release-hold", "LIVE"],
                capture_output=True, text=True,
            )
            assert result.returncode != 0


class TestBrowserCliDeterministic:
    def test_deterministic_rerun(self):
        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2:
            for out in (out1, out2):
                subprocess.run(
                    [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                     "--quality-dir", str(FIXTURES / "quality_bundle_pass"),
                     "--output-dir", out, "--strict", "--release-hold", "HOLD"],
                    capture_output=True, text=True,
                )
            # Compare JSON artifacts (skip HTML/MD which contain generated_at)
            for name in ["artifact_browser_index.json", "artifact_schema_validation.json",
                         "review_model.json", "human_review_checklist.json",
                         "artifact_browser_manifest.json"]:
                j1 = json.loads((Path(out1) / name).read_text())
                j2 = json.loads((Path(out2) / name).read_text())
                # Normalize generated_at
                j1.pop("generated_at", None)
                j2.pop("generated_at", None)
                assert json.dumps(j1, sort_keys=True) == json.dumps(j2, sort_keys=True), \
                    f"Diff in {name}"


class TestCompareIdenticalBrowsers:
    def test_identical_pass(self):
        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2, \
                tempfile.TemporaryDirectory() as cmp:
            for out in (out1, out2):
                subprocess.run(
                    [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                     "--quality-dir", str(FIXTURES / "quality_bundle_pass"),
                     "--output-dir", out, "--strict", "--release-hold", "HOLD"],
                    capture_output=True, text=True,
                )
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "compare_research_artifact_browsers.py"),
                 "--left", out1, "--right", out2,
                 "--output-dir", cmp, "--require-identical-safety-flags"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"stderr: {result.stderr}"
            assert "PASS" in result.stdout

    def test_diff_json_created(self):
        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2, \
                tempfile.TemporaryDirectory() as cmp:
            for out in (out1, out2):
                subprocess.run(
                    [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                     "--quality-dir", str(FIXTURES / "quality_bundle_pass"),
                     "--output-dir", out, "--strict", "--release-hold", "HOLD"],
                    capture_output=True, text=True,
                )
            subprocess.run(
                [sys.executable, str(SCRIPTS / "compare_research_artifact_browsers.py"),
                 "--left", out1, "--right", out2,
                 "--output-dir", cmp, "--require-identical-safety-flags"],
                capture_output=True, text=True,
            )
            assert (Path(cmp) / "artifact_browser_diff.json").exists()
            assert (Path(cmp) / "artifact_browser_diff.md").exists()


class TestCompareChangedHash:
    def test_changed_hash_reports_diff(self):
        left_dir = FIXTURES / "quality_bundle_pass"
        right_dir = FIXTURES / "quality_bundle_changed"

        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2:
            # Build browser for both
            for qd, out in [(left_dir, out1), (right_dir, out2)]:
                subprocess.run(
                    [sys.executable, str(SCRIPTS / "build_research_artifact_browser.py"),
                     "--quality-dir", str(qd),
                     "--output-dir", out, "--strict", "--release-hold", "HOLD"],
                    capture_output=True, text=True,
                )

            result = compare_browser_outputs(Path(out1), Path(out2))
            assert len(result.changed_artifacts) > 0
            assert result.identical_safety_flags is True

    def test_compare_api_level(self):
        left_dir = FIXTURES / "quality_bundle_pass"
        right_dir = FIXTURES / "quality_bundle_changed"

        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2:
            for qd, out in [(left_dir, out1), (right_dir, out2)]:
                idx = artifact_browser_index_to_dict(build_artifact_browser_index(qd))
                review = review_model_to_dict(build_review_model(qd))
                schema = schema_validation_to_dict(validate_artifact_schema(qd))
                (Path(out) / "artifact_browser_index.json").write_text(
                    json.dumps(idx, sort_keys=True))
                (Path(out) / "review_model.json").write_text(
                    json.dumps(review, sort_keys=True))

            result = compare_browser_outputs(Path(out1), Path(out2))
            assert result.identical_safety_flags is True


class TestCompareSafetyFlagMismatch:
    def test_safety_mismatch_fail(self):
        left_dir = FIXTURES / "quality_bundle_pass"
        right_dir = FIXTURES / "quality_bundle_invalid_safety"

        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2:
            # Build browsers
            for qd, out in [(left_dir, out1), (right_dir, out2)]:
                idx = artifact_browser_index_to_dict(build_artifact_browser_index(qd))
                review = review_model_to_dict(build_review_model(qd))
                (Path(out) / "artifact_browser_index.json").write_text(
                    json.dumps(idx, sort_keys=True))
                (Path(out) / "review_model.json").write_text(
                    json.dumps(review, sort_keys=True))

            result = compare_browser_outputs(
                Path(out1), Path(out2), require_identical_safety_flags=True)
            assert result.status == "FAIL"
            assert result.identical_safety_flags is False
            assert len(result.safety_flag_diff) > 0


class TestCompareCli:
    def test_compare_cli_safety_mismatch_fail(self):
        left_dir = FIXTURES / "quality_bundle_pass"
        right_dir = FIXTURES / "quality_bundle_invalid_safety"

        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2, \
                tempfile.TemporaryDirectory() as cmp:
            for qd, out in [(left_dir, out1), (right_dir, out2)]:
                idx = artifact_browser_index_to_dict(build_artifact_browser_index(qd))
                review = review_model_to_dict(build_review_model(qd))
                (Path(out) / "artifact_browser_index.json").write_text(
                    json.dumps(idx, sort_keys=True))
                (Path(out) / "review_model.json").write_text(
                    json.dumps(review, sort_keys=True))

            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "compare_research_artifact_browsers.py"),
                 "--left", out1, "--right", out2,
                 "--output-dir", cmp, "--require-identical-safety-flags"],
                capture_output=True, text=True,
            )
            assert result.returncode != 0
            assert "FAIL" in result.stdout


class TestComparisonMarkdown:
    def test_diff_markdown_content(self):
        left_dir = FIXTURES / "quality_bundle_pass"
        right_dir = FIXTURES / "quality_bundle_changed"

        with tempfile.TemporaryDirectory() as out1, tempfile.TemporaryDirectory() as out2:
            for qd, out in [(left_dir, out1), (right_dir, out2)]:
                idx = artifact_browser_index_to_dict(build_artifact_browser_index(qd))
                review = review_model_to_dict(build_review_model(qd))
                (Path(out) / "artifact_browser_index.json").write_text(
                    json.dumps(idx, sort_keys=True))
                (Path(out) / "review_model.json").write_text(
                    json.dumps(review, sort_keys=True))

            result = compare_browser_outputs(Path(out1), Path(out2))
            md = comparison_to_markdown(result)
            assert "Artifact Browser Comparison" in md
            assert "Advisory only" in md
            assert "HOLD" in md
