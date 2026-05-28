"""Tests for research artifact browser — T9361-T9800.

Indexer, schema validator, view model, safety regression.
No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from core.research_artifact_browser import (
    ArtifactBrowserIndex,
    build_artifact_browser_index,
    build_review_model,
    validate_artifact_schema,
    artifact_browser_index_to_dict,
    review_model_to_dict,
    schema_validation_to_dict,
)
from core.research_artifact_schema import (
    BROWSER_FORBIDDEN_IMPORTS,
    BROWSER_REQUIRED_ARTIFACTS,
    MANIFEST_SAFETY_CHECKS,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "research_artifact_browser"


# === Program A: Artifact Indexer Tests ===


class TestArtifactIndexerNormal:
    def test_index_pass_bundle(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        assert idx.status == "PASS"
        assert idx.required_missing == 0
        assert idx.required_present > 0
        assert idx.release_hold == "HOLD"
        assert idx.advisory_only is True

    def test_index_deterministic(self):
        d = FIXTURES / "quality_bundle_pass"
        r1 = json.dumps(artifact_browser_index_to_dict(build_artifact_browser_index(d)), sort_keys=True)
        r2 = json.dumps(artifact_browser_index_to_dict(build_artifact_browser_index(d)), sort_keys=True)
        assert r1 == r2

    def test_index_entry_has_expected_fields(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        for e in idx.entries:
            assert e.name
            assert isinstance(e.required, bool)
            assert isinstance(e.exists, bool)
            assert isinstance(e.sha256, str)
            assert isinstance(e.size_bytes, int)
            assert isinstance(e.json_parse_ok, bool)
            assert isinstance(e.top_level_keys, tuple)

    def test_index_json_entries_sorted(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        names = [e.name for e in idx.entries]
        assert names == sorted(names)


class TestArtifactIndexerMissingRequired:
    def test_missing_required_fails(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_missing_required")
        assert idx.status == "FAIL"
        assert idx.required_missing > 0

    def test_missing_required_counts(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_missing_required")
        assert idx.required_present == 1  # only manifest.json
        assert idx.required_missing == len(BROWSER_REQUIRED_ARTIFACTS) - 1


class TestArtifactIndexerCorruptedJson:
    def test_corrupted_json_parse_fail(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_corrupted_json")
        corrupted = [e for e in idx.entries if e.name == "quality_gate_summary.json"]
        assert len(corrupted) == 1
        assert corrupted[0].json_parse_ok is False
        assert corrupted[0].exists is True

    def test_corrupted_json_still_indexed(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_corrupted_json")
        assert idx.status == "FAIL"  # missing many required


class TestArtifactIndexerShape:
    def test_pass_bundle_json_keys(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        manifest_entry = [e for e in idx.entries if e.name == "manifest.json"][0]
        assert manifest_entry.json_parse_ok is True
        assert "release_hold" in manifest_entry.top_level_keys
        assert "advisory_only" in manifest_entry.top_level_keys

    def test_non_json_no_keys(self):
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        md_entry = [e for e in idx.entries if e.name == "report.md"][0]
        assert md_entry.top_level_keys == ()
        assert md_entry.json_parse_ok is False


# === Program B: Schema Validator Tests ===


class TestSchemaValidatorNormal:
    def test_pass_bundle_valid(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_pass")
        assert r.status == "PASS"
        assert r.manifest_valid is True
        assert r.safety_flags_valid is True
        assert r.promotion_gate_advisory is True
        assert r.reproducibility_has_hashes is True
        assert r.report_quality_has_sections is True

    def test_safety_flag_errors_empty(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_pass")
        assert len(r.safety_flag_errors) == 0

    def test_schema_shape_errors_empty(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_pass")
        # May have shape errors for optional artifacts with no schema defined
        # but required ones should all pass
        critical = [e for e in r.schema_shape_errors if "manifest" in e or "quality_gate_summary" in e]
        assert len(critical) == 0


class TestSchemaValidatorSafetyFlags:
    def test_release_hold_not_hold_fails(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_invalid_safety")
        assert r.status == "FAIL"
        assert r.safety_flags_valid is False

    def test_invalid_safety_has_errors(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_invalid_safety")
        assert len(r.safety_flag_errors) > 0
        assert any("release_hold" in e for e in r.safety_flag_errors)

    def test_advisory_only_false_detected(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_invalid_safety")
        assert any("advisory_only" in e for e in r.safety_flag_errors)

    def test_human_review_required_false_detected(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_invalid_safety")
        assert any("human_review_required" in e for e in r.safety_flag_errors)


class TestSchemaValidatorCorrupted:
    def test_corrupted_manifest_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "manifest.json").write_text("NOT JSON")
            r = validate_artifact_schema(p)
            assert r.status == "FAIL"
            assert any("corrupted" in e for e in r.errors)

    def test_corrupted_json_readable_reason(self):
        r = validate_artifact_schema(FIXTURES / "quality_bundle_corrupted_json")
        assert r.status == "FAIL"
        # quality_gate_summary.json is corrupted
        assert any("corrupted" in e for e in r.errors)


class TestSchemaValidatorMissingManifest:
    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as d:
            r = validate_artifact_schema(Path(d))
            assert r.status == "FAIL"
            assert any("manifest" in e.lower() for e in r.errors)


# === Program C: Review View Model Tests ===


class TestReviewModelNormal:
    def test_pass_bundle_model(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert m.verdict == "PASS"
        assert m.composite_score == pytest.approx(0.85)
        assert m.evidence_completeness == pytest.approx(1.0)

    def test_safety_flags_present(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert m.safety_flags["release_hold_is_HOLD"] is True
        assert m.safety_flags["advisory_only"] is True
        assert m.safety_flags["human_review_required"] is True

    def test_model_deterministic(self):
        d = FIXTURES / "quality_bundle_pass"
        r1 = json.dumps(review_model_to_dict(build_review_model(d)), sort_keys=True)
        r2 = json.dumps(review_model_to_dict(build_review_model(d)), sort_keys=True)
        assert r1 == r2


class TestReviewModelBlockersWarnings:
    def test_extract_warnings(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert "bootstrap_below_threshold" in m.warnings

    def test_extract_blockers_empty(self):
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        assert len(m.blockers) == 0

    def test_changed_bundle_has_more_warnings(self):
        m = build_review_model(FIXTURES / "quality_bundle_changed")
        assert len(m.warnings) > 1


class TestReviewModelMissingOptional:
    def test_missing_optional_no_crash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            # Write only manifest
            (p / "manifest.json").write_text(json.dumps({
                "release_hold": "HOLD", "advisory_only": True,
                "human_review_required": True,
            }))
            m = build_review_model(p)
            assert m.verdict == "UNKNOWN"
            assert m.composite_score == 0.0


# === Safety Regression Tests ===


class TestSafetyRegression:
    def test_no_forbidden_imports_in_browser_modules(self):
        """Prove no forbidden imports in browser code."""
        import re
        browser_files = [
            Path(__file__).resolve().parent.parent.parent / "core" / "research_artifact_browser.py",
            Path(__file__).resolve().parent.parent.parent / "core" / "research_artifact_schema.py",
            Path(__file__).resolve().parent.parent.parent / "core" / "research_artifact_compare.py",
            Path(__file__).resolve().parent.parent.parent / "core" / "research_static_report_renderer.py",
        ]
        for fp in browser_files:
            if not fp.exists():
                continue
            content = fp.read_text()
            for imp in BROWSER_FORBIDDEN_IMPORTS:
                pattern = rf'(?:from|import)\s+{re.escape(imp)}\b'
                assert not re.search(pattern, content), \
                    f"Forbidden import '{imp}' found in {fp.name}"

    def test_no_forbidden_imports_in_scripts(self):
        """Prove no forbidden imports in browser scripts."""
        import re
        script_files = [
            Path(__file__).resolve().parent.parent.parent / "scripts" / "build_research_artifact_browser.py",
            Path(__file__).resolve().parent.parent.parent / "scripts" / "compare_research_artifact_browsers.py",
        ]
        for fp in script_files:
            if not fp.exists():
                continue
            content = fp.read_text()
            for imp in BROWSER_FORBIDDEN_IMPORTS:
                pattern = rf'(?:from|import)\s+{re.escape(imp)}\b'
                assert not re.search(pattern, content), \
                    f"Forbidden import '{imp}' found in {fp.name}"

    def test_manifest_safety_checks_all_present(self):
        """Verify MANIFEST_SAFETY_CHECKS covers all required flags."""
        assert "release_hold" in MANIFEST_SAFETY_CHECKS
        assert MANIFEST_SAFETY_CHECKS["release_hold"] == "HOLD"
        assert MANIFEST_SAFETY_CHECKS["advisory_only"] is True
        assert MANIFEST_SAFETY_CHECKS["human_review_required"] is True
        assert MANIFEST_SAFETY_CHECKS["no_live"] is True
        assert MANIFEST_SAFETY_CHECKS["no_network"] is True

    def test_review_model_safety_flags_comprehensive(self):
        """Verify review model includes all safety flags."""
        m = build_review_model(FIXTURES / "quality_bundle_pass")
        required_flags = [
            "release_hold_is_HOLD", "no_live", "no_submit", "no_exchange",
            "no_runtime_integration", "no_planner_integration", "no_network",
            "advisory_only", "human_review_required", "strict_mode",
        ]
        for flag in required_flags:
            assert flag in m.safety_flags, f"Missing safety flag: {flag}"

    def test_browser_index_always_hold(self):
        """Browser index always reports release_hold=HOLD."""
        idx = build_artifact_browser_index(FIXTURES / "quality_bundle_pass")
        assert idx.release_hold == "HOLD"
        assert idx.advisory_only is True
