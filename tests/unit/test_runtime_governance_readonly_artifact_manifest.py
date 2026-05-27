"""Tests for T854: runtime governance read-only artifact manifest."""
from core.runtime_governance_readonly_artifact_manifest import (
    RuntimeGovernanceReadOnlyArtifact,
    build_readonly_artifact_manifest,
    readonly_artifact_manifest_to_dict,
    readonly_artifact_manifest_to_markdown,
    summarize_readonly_artifact_manifest,
)


def test_artifact_count():
    artifacts = build_readonly_artifact_manifest()
    assert len(artifacts) == 84


def test_includes_core_test_doc_for_each_task():
    artifacts = build_readonly_artifact_manifest()
    by_task: dict[str, list[str]] = {}
    for a in artifacts:
        by_task.setdefault(a.task_id, []).append(a.artifact_type)
    for task_num in range(826, 854):
        tid = f"T{task_num}"
        assert sorted(by_task[tid]) == ["core", "doc", "test"]


def test_task_ids_range():
    artifacts = build_readonly_artifact_manifest()
    task_ids = sorted({a.task_id for a in artifacts})
    expected = [f"T{n}" for n in range(826, 854)]
    assert task_ids == expected


def test_artifact_types_valid():
    artifacts = build_readonly_artifact_manifest()
    for a in artifacts:
        assert a.artifact_type in ("core", "test", "doc")


def test_deterministic():
    a1 = build_readonly_artifact_manifest()
    a2 = build_readonly_artifact_manifest()
    assert a1 == a2


def test_frozen():
    artifacts = build_readonly_artifact_manifest()
    a = artifacts[0]
    try:
        a.task_id = "X"  # type: ignore[misc]
        assert False, "should be frozen"
    except AttributeError:
        pass


def test_to_dict_returns_list_of_dicts():
    artifacts = build_readonly_artifact_manifest()
    result = readonly_artifact_manifest_to_dict(artifacts)
    assert isinstance(result, list)
    assert len(result) == 84
    assert isinstance(result[0], dict)
    assert set(result[0].keys()) == {"task_id", "artifact_type", "path", "purpose"}


def test_to_markdown_contains_header():
    artifacts = build_readonly_artifact_manifest()
    md = readonly_artifact_manifest_to_markdown(artifacts)
    assert "# Runtime Governance Read-Only Artifact Manifest" in md
    assert "| Task ID |" in md


def test_summarize_total():
    artifacts = build_readonly_artifact_manifest()
    summary = summarize_readonly_artifact_manifest(artifacts)
    assert summary["total"] == 84


def test_summarize_by_type():
    artifacts = build_readonly_artifact_manifest()
    summary = summarize_readonly_artifact_manifest(artifacts)
    assert summary["by_type"] == {"core": 28, "test": 28, "doc": 28}


def test_summarize_by_task_count():
    artifacts = build_readonly_artifact_manifest()
    summary = summarize_readonly_artifact_manifest(artifacts)
    assert len(summary["by_task"]) == 28
    for count in summary["by_task"].values():
        assert count == 3
