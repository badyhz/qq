"""Tests for runtime_governance_artifact_index — T794-T818 static index."""

from __future__ import annotations

import pytest

from core.runtime_governance_artifact_index import (
    RuntimeGovernanceArtifact,
    artifact_index_to_dict,
    artifact_index_to_markdown,
    build_runtime_governance_artifact_index,
    summarize_artifact_index,
)


class TestBuildArtifactIndex:
    def test_returns_75_artifacts(self):
        artifacts = build_runtime_governance_artifact_index()
        assert len(artifacts) == 75

    def test_covers_t794_to_t818(self):
        artifacts = build_runtime_governance_artifact_index()
        task_ids = sorted({a.task_id for a in artifacts})
        expected = [f"T{i}" for i in range(794, 819)]
        assert task_ids == expected

    def test_each_task_has_3_artifacts(self):
        artifacts = build_runtime_governance_artifact_index()
        from collections import Counter
        counts = Counter(a.task_id for a in artifacts)
        for tid, count in counts.items():
            assert count == 3, f"{tid} has {count} artifacts, expected 3"

    def test_artifact_types_coverage(self):
        artifacts = build_runtime_governance_artifact_index()
        from collections import Counter
        by_type = Counter(a.artifact_type for a in artifacts)
        assert by_type["core"] == 25
        assert by_type["test"] == 25
        assert by_type["doc"] == 25

    def test_frozen_dataclass(self):
        artifacts = build_runtime_governance_artifact_index()
        a = artifacts[0]
        with pytest.raises(AttributeError):
            a.task_id = "X"  # type: ignore[misc]

    def test_artifact_ids_unique(self):
        artifacts = build_runtime_governance_artifact_index()
        ids = [a.artifact_id for a in artifacts]
        assert len(ids) == len(set(ids))

    def test_core_paths_start_with_core(self):
        artifacts = build_runtime_governance_artifact_index()
        for a in artifacts:
            if a.artifact_type == "core":
                assert a.path.startswith("core/")

    def test_test_paths_start_with_tests(self):
        artifacts = build_runtime_governance_artifact_index()
        for a in artifacts:
            if a.artifact_type == "test":
                assert a.path.startswith("tests/unit/")

    def test_doc_paths_start_with_docs(self):
        artifacts = build_runtime_governance_artifact_index()
        for a in artifacts:
            if a.artifact_type == "doc":
                assert a.path.startswith("docs/")


class TestArtifactIndexToDict:
    def test_returns_list_of_dicts(self):
        artifacts = build_runtime_governance_artifact_index()
        result = artifact_index_to_dict(artifacts)
        assert isinstance(result, list)
        assert len(result) == 75
        assert isinstance(result[0], dict)

    def test_dict_keys(self):
        artifacts = build_runtime_governance_artifact_index()
        result = artifact_index_to_dict(artifacts)
        expected_keys = {"artifact_id", "task_id", "artifact_type", "path", "purpose"}
        assert set(result[0].keys()) == expected_keys

    def test_round_trip_preserves_count(self):
        artifacts = build_runtime_governance_artifact_index()
        dicts = artifact_index_to_dict(artifacts)
        assert len(dicts) == len(artifacts)


class TestArtifactIndexToMarkdown:
    def test_deterministic(self):
        artifacts = build_runtime_governance_artifact_index()
        md1 = artifact_index_to_markdown(artifacts)
        md2 = artifact_index_to_markdown(artifacts)
        assert md1 == md2

    def test_contains_header(self):
        artifacts = build_runtime_governance_artifact_index()
        md = artifact_index_to_markdown(artifacts)
        assert "# Runtime Governance Artifact Index" in md

    def test_contains_table_separator(self):
        artifacts = build_runtime_governance_artifact_index()
        md = artifact_index_to_markdown(artifacts)
        assert "|-------------|------|------|------|" in md

    def test_contains_all_artifact_ids(self):
        artifacts = build_runtime_governance_artifact_index()
        md = artifact_index_to_markdown(artifacts)
        for a in artifacts:
            assert a.artifact_id in md

    def test_no_timestamps(self):
        artifacts = build_runtime_governance_artifact_index()
        md = artifact_index_to_markdown(artifacts)
        # Should not contain common timestamp patterns
        assert "202" not in md.split("\n")[0]  # no year in header


class TestSummarizeArtifactIndex:
    def test_total(self):
        artifacts = build_runtime_governance_artifact_index()
        summary = summarize_artifact_index(artifacts)
        assert summary["total"] == 75

    def test_tasks(self):
        artifacts = build_runtime_governance_artifact_index()
        summary = summarize_artifact_index(artifacts)
        assert summary["tasks"] == 25

    def test_by_type(self):
        artifacts = build_runtime_governance_artifact_index()
        summary = summarize_artifact_index(artifacts)
        assert summary["by_type"] == {"core": 25, "doc": 25, "test": 25}

    def test_artifacts_per_task(self):
        artifacts = build_runtime_governance_artifact_index()
        summary = summarize_artifact_index(artifacts)
        for tid, count in summary["artifacts_per_task"].items():
            assert count == 3, f"{tid} has {count}"

    def test_deterministic(self):
        artifacts = build_runtime_governance_artifact_index()
        s1 = summarize_artifact_index(artifacts)
        s2 = summarize_artifact_index(artifacts)
        assert s1 == s2
