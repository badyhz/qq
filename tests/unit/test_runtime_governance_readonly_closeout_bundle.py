"""T841: Tests for runtime governance read-only closeout bundle."""

import pytest

from core.runtime_governance_readonly_closeout_bundle import (
    RuntimeGovernanceReadOnlyCloseoutBundle,
    build_readonly_closeout_bundle,
    readonly_closeout_bundle_to_dict,
    readonly_closeout_bundle_to_markdown,
)


class TestBuildReadonlyCloseoutBundle:
    """Test bundle construction."""

    def test_default_bundle_is_pass(self):
        """Default build (all sub-components pass) yields final_status=PASS."""
        bundle = build_readonly_closeout_bundle()
        assert bundle.final_status == "PASS"

    def test_all_summaries_present(self):
        """All six summary dicts are populated."""
        bundle = build_readonly_closeout_bundle()
        assert isinstance(bundle.manifest_summary, dict)
        assert len(bundle.manifest_summary) > 0
        assert isinstance(bundle.regression_summary, dict)
        assert len(bundle.regression_summary) > 0
        assert isinstance(bundle.readiness_summary, dict)
        assert len(bundle.readiness_summary) > 0
        assert isinstance(bundle.blocker_summary, dict)
        assert len(bundle.blocker_summary) > 0
        assert isinstance(bundle.evidence_summary, dict)
        assert len(bundle.evidence_summary) > 0
        assert isinstance(bundle.checklist_summary, dict)
        assert len(bundle.checklist_summary) > 0

    def test_deterministic(self):
        """Multiple builds produce identical output."""
        a = build_readonly_closeout_bundle()
        b = build_readonly_closeout_bundle()
        assert a == b

    def test_frozen(self):
        """Bundle is frozen (immutable)."""
        bundle = build_readonly_closeout_bundle()
        with pytest.raises(AttributeError):
            bundle.final_status = "FAIL"  # type: ignore[misc]


class TestSerialization:
    """Test to_dict and to_markdown."""

    def test_to_dict_has_expected_keys(self):
        """to_dict output has all required keys."""
        bundle = build_readonly_closeout_bundle()
        d = readonly_closeout_bundle_to_dict(bundle)
        expected_keys = {
            "manifest_summary",
            "regression_summary",
            "readiness_summary",
            "blocker_summary",
            "evidence_summary",
            "checklist_summary",
            "final_status",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_deterministic(self):
        """to_dict produces identical output across calls."""
        bundle = build_readonly_closeout_bundle()
        d1 = readonly_closeout_bundle_to_dict(bundle)
        d2 = readonly_closeout_bundle_to_dict(bundle)
        assert d1 == d2

    def test_markdown_contains_final_status(self):
        """Markdown output contains the final_status string."""
        bundle = build_readonly_closeout_bundle()
        md = readonly_closeout_bundle_to_markdown(bundle)
        assert bundle.final_status in md
        assert "Final Status" in md

    def test_markdown_deterministic(self):
        """Markdown output is deterministic."""
        bundle = build_readonly_closeout_bundle()
        md1 = readonly_closeout_bundle_to_markdown(bundle)
        md2 = readonly_closeout_bundle_to_markdown(bundle)
        assert md1 == md2
