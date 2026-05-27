"""Tests for runtime governance engineering closeout bundle.

Sync only. No async. No I/O. No network. No random.
"""

from __future__ import annotations

import pytest

from core.runtime_governance_engineering_closeout_bundle import (
    RuntimeGovernanceEngineeringCloseoutBundle,
    build_runtime_governance_engineering_closeout_bundle,
    engineering_closeout_bundle_to_dict,
    engineering_closeout_bundle_to_markdown,
)


# -- default bundle status --


class TestDefaultBundleNotFail:
    def test_default_bundle_not_fail(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()

        assert bundle.final_status != "FAIL"

    def test_default_bundle_warn(self):
        """Default has PROCEED_TO_MANUAL_SCOPE_ONLY -> WARN (review item)."""
        bundle = build_runtime_governance_engineering_closeout_bundle()

        assert bundle.final_status == "WARN"


class TestDefaultBundleHasAllSummaries:
    def test_all_summary_keys_present(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()

        assert bundle.stack_manifest_summary
        assert bundle.regression_summary
        assert bundle.phase_control_summary
        assert bundle.manual_scope_summary
        assert bundle.risk_register_summary
        assert artifact_index_summary_present(bundle)
        assert bundle.closeout_summary


def artifact_index_summary_present(bundle):
    return bool(bundle.artifact_index_summary)


class TestDefaultBundleTitle:
    def test_default_title(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()

        assert "Engineering Closeout Bundle" in bundle.title


# -- dict deterministic --


class TestDictDeterministic:
    def test_dict_same_on_repeat(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()
        d1 = engineering_closeout_bundle_to_dict(bundle)
        d2 = engineering_closeout_bundle_to_dict(bundle)

        assert d1 == d2

    def test_dict_keys(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()
        d = engineering_closeout_bundle_to_dict(bundle)

        expected_keys = {
            "title",
            "stack_manifest_summary",
            "regression_summary",
            "phase_control_summary",
            "manual_scope_summary",
            "risk_register_summary",
            "artifact_index_summary",
            "closeout_summary",
            "final_status",
            "notes",
        }
        assert expected_keys == set(d.keys())


class TestDictContainsFinalStatus:
    def test_dict_final_status(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()
        d = engineering_closeout_bundle_to_dict(bundle)

        assert d["final_status"] in {"PASS", "WARN", "FAIL"}


# -- markdown deterministic --


class TestMarkdownDeterministic:
    def test_markdown_same_on_repeat(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()
        md1 = engineering_closeout_bundle_to_markdown(bundle)
        md2 = engineering_closeout_bundle_to_markdown(bundle)

        assert md1 == md2


class TestMarkdownContainsSections:
    def test_markdown_has_all_sections(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()
        md = engineering_closeout_bundle_to_markdown(bundle)

        assert "# Runtime Governance Engineering Closeout Bundle" in md
        assert "## Stack Manifest" in md
        assert "## Regression Packet" in md
        assert "## Phase Control Report" in md
        assert "## Manual Scope Packet" in md
        assert "## Integration Risk Register" in md
        assert "## Artifact Index" in md
        assert "## Closeout Checklist" in md


class TestMarkdownContainsFinalStatus:
    def test_markdown_contains_final_status(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()
        md = engineering_closeout_bundle_to_markdown(bundle)

        assert "**Final Status:** WARN" in md


class TestBundleFrozen:
    def test_bundle_is_frozen(self):
        bundle = build_runtime_governance_engineering_closeout_bundle()

        with pytest.raises(AttributeError):
            bundle.final_status = "PASS"


class TestCustomTitle:
    def test_custom_title(self):
        bundle = build_runtime_governance_engineering_closeout_bundle(
            title="Custom Bundle"
        )

        assert bundle.title == "Custom Bundle"

        md = engineering_closeout_bundle_to_markdown(bundle)
        assert "# Custom Bundle" in md
