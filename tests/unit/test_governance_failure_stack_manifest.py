"""Tests for governance failure stack manifest. Pure, deterministic."""

from __future__ import annotations

import pytest

from core.governance_failure_stack_manifest import (
    ComponentStatus,
    GovernanceStackComponent,
    GovernanceStackManifest,
    build_expected_governance_stack_manifest,
    manifest_to_dict,
    manifest_to_markdown,
    summarize_manifest,
)


class TestBuildExpectedManifest:
    def test_has_t786_to_t789(self):
        m = build_expected_governance_stack_manifest()
        task_ids = [c.task_id for c in m.components]
        assert task_ids == ["T786", "T787", "T788", "T789"]

    def test_default_all_complete(self):
        m = build_expected_governance_stack_manifest()
        assert m.verdict == "PASS"
        assert m.completed_components == 4
        assert m.missing_components == 0

    def test_partial_warn(self):
        m = build_expected_governance_stack_manifest(
            statuses={"T788": ComponentStatus.PARTIAL}
        )
        assert m.verdict == "WARN"
        assert m.completed_components == 3

    def test_missing_fail(self):
        m = build_expected_governance_stack_manifest(
            statuses={"T789": ComponentStatus.MISSING}
        )
        assert m.verdict == "FAIL"
        assert m.missing_components == 1

    def test_missing_overrides_partial(self):
        """FAIL if any missing, even with partials."""
        m = build_expected_governance_stack_manifest(
            statuses={
                "T786": ComponentStatus.PARTIAL,
                "T787": ComponentStatus.MISSING,
            }
        )
        assert m.verdict == "FAIL"


class TestDeterminism:
    def test_repeated_calls_identical(self):
        m1 = build_expected_governance_stack_manifest()
        m2 = build_expected_governance_stack_manifest()
        assert manifest_to_dict(m1) == manifest_to_dict(m2)

    def test_component_ordering_stable(self):
        m = build_expected_governance_stack_manifest()
        ids = [c.task_id for c in m.components]
        assert ids == sorted(ids, key=lambda x: int(x[1:]))

    def test_markdown_deterministic(self):
        m = build_expected_governance_stack_manifest()
        md1 = manifest_to_markdown(m)
        md2 = manifest_to_markdown(m)
        assert md1 == md2


class TestSerialization:
    def test_dict_roundtrip(self):
        m = build_expected_governance_stack_manifest()
        d = manifest_to_dict(m)
        assert d["title"] == "Governance Failure Stack Manifest"
        assert d["verdict"] == "PASS"
        assert d["total_components"] == 4
        assert len(d["components"]) == 4
        assert d["components"][0]["task_id"] == "T786"

    def test_dict_status_values(self):
        m = build_expected_governance_stack_manifest(
            statuses={"T788": ComponentStatus.PARTIAL}
        )
        d = manifest_to_dict(m)
        statuses = {c["task_id"]: c["status"] for c in d["components"]}
        assert statuses["T788"] == "PARTIAL"


class TestMarkdown:
    def test_contains_verdict(self):
        m = build_expected_governance_stack_manifest()
        md = manifest_to_markdown(m)
        assert "**Verdict:** PASS" in md

    def test_contains_all_tasks(self):
        m = build_expected_governance_stack_manifest()
        md = manifest_to_markdown(m)
        for tid in ["T786", "T787", "T788", "T789"]:
            assert tid in md


class TestSummarize:
    def test_counts_correct(self):
        m = build_expected_governance_stack_manifest()
        s = summarize_manifest(m)
        assert s["total"] == 4
        assert s["completed"] == 4
        assert s["missing"] == 0
        assert s["verdict"] == "PASS"

    def test_by_status(self):
        m = build_expected_governance_stack_manifest(
            statuses={
                "T786": ComponentStatus.COMPLETE,
                "T787": ComponentStatus.PARTIAL,
                "T788": ComponentStatus.MISSING,
                "T789": ComponentStatus.COMPLETE,
            }
        )
        s = summarize_manifest(m)
        assert s["by_status"]["COMPLETE"] == 2
        assert s["by_status"]["PARTIAL"] == 1
        assert s["by_status"]["MISSING"] == 1
        assert s["verdict"] == "FAIL"
