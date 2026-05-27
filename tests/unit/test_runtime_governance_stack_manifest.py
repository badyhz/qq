"""Tests for core.runtime_governance_stack_manifest."""

from __future__ import annotations

import pytest

from core.runtime_governance_stack_manifest import (
    RuntimeGovernanceStackComponent,
    RuntimeGovernanceStackManifest,
    build_expected_runtime_governance_stack_manifest,
    runtime_manifest_to_dict,
    runtime_manifest_to_markdown,
    summarize_runtime_manifest,
)


# ── build_expected_runtime_governance_stack_manifest ────────────────


class TestBuildManifest:
    def test_manifest_includes_12_components(self):
        m = build_expected_runtime_governance_stack_manifest()
        assert len(m.components) == 12

    def test_all_components_pass(self):
        m = build_expected_runtime_governance_stack_manifest()
        for c in m.components:
            assert c.status == "PASS"

    def test_total_equals_completed_equals_12(self):
        m = build_expected_runtime_governance_stack_manifest()
        assert m.total_components == 12
        assert m.completed_components == 12

    def test_verdict_pass(self):
        m = build_expected_runtime_governance_stack_manifest()
        assert m.verdict == "PASS"

    def test_verdict_warn_when_one_warn(self):
        m = build_expected_runtime_governance_stack_manifest(
            overrides={"T796": "WARN"},
        )
        assert m.verdict == "WARN"

    def test_verdict_fail_when_one_fail(self):
        m = build_expected_runtime_governance_stack_manifest(
            overrides={"T800": "FAIL"},
        )
        assert m.verdict == "FAIL"

    def test_components_cover_t794_through_t805(self):
        m = build_expected_runtime_governance_stack_manifest()
        ids = [c.task_id for c in m.components]
        expected = [f"T{i}" for i in range(794, 806)]
        assert ids == expected


# ── runtime_manifest_to_dict ────────────────────────────────────────


class TestManifestToDict:
    def test_dict_deterministic(self):
        m = build_expected_runtime_governance_stack_manifest()
        d1 = runtime_manifest_to_dict(m)
        d2 = runtime_manifest_to_dict(m)
        assert d1 == d2

    def test_dict_keys(self):
        m = build_expected_runtime_governance_stack_manifest()
        d = runtime_manifest_to_dict(m)
        assert set(d.keys()) == {
            "title",
            "components",
            "total_components",
            "completed_components",
            "verdict",
        }

    def test_component_dict_keys(self):
        m = build_expected_runtime_governance_stack_manifest()
        d = runtime_manifest_to_dict(m)
        c = d["components"][0]
        assert set(c.keys()) == {
            "task_id",
            "name",
            "module_path",
            "test_path",
            "doc_path",
            "status",
            "notes",
        }


# ── runtime_manifest_to_markdown ────────────────────────────────────


class TestManifestToMarkdown:
    def test_markdown_deterministic(self):
        m = build_expected_runtime_governance_stack_manifest()
        md1 = runtime_manifest_to_markdown(m)
        md2 = runtime_manifest_to_markdown(m)
        assert md1 == md2

    def test_markdown_contains_all_task_ids(self):
        m = build_expected_runtime_governance_stack_manifest()
        md = runtime_manifest_to_markdown(m)
        for i in range(794, 806):
            assert f"T{i}" in md

    def test_markdown_contains_title(self):
        m = build_expected_runtime_governance_stack_manifest()
        md = runtime_manifest_to_markdown(m)
        assert "Runtime Governance Stack Manifest" in md

    def test_markdown_contains_verdict(self):
        m = build_expected_runtime_governance_stack_manifest()
        md = runtime_manifest_to_markdown(m)
        assert "**Verdict:** PASS" in md


# ── summarize_runtime_manifest ──────────────────────────────────────


class TestSummarizeManifest:
    def test_summarize_all_pass(self):
        m = build_expected_runtime_governance_stack_manifest()
        s = summarize_runtime_manifest(m)
        assert s["total"] == 12
        assert s["completed"] == 12
        assert s["by_status"] == {"PASS": 12}
        assert s["verdict"] == "PASS"

    def test_summarize_with_warn(self):
        m = build_expected_runtime_governance_stack_manifest(
            overrides={"T796": "WARN"},
        )
        s = summarize_runtime_manifest(m)
        assert s["total"] == 12
        assert s["completed"] == 11
        assert s["by_status"] == {"PASS": 11, "WARN": 1}
        assert s["verdict"] == "WARN"

    def test_summarize_with_fail(self):
        m = build_expected_runtime_governance_stack_manifest(
            overrides={"T800": "FAIL"},
        )
        s = summarize_runtime_manifest(m)
        assert s["total"] == 12
        assert s["completed"] == 11
        assert s["by_status"] == {"FAIL": 1, "PASS": 11}
        assert s["verdict"] == "FAIL"
