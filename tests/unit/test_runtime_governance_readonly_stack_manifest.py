import pytest

from core.runtime_governance_readonly_stack_manifest import (
    RuntimeGovernanceReadOnlyStackComponent,
    build_readonly_stack_manifest,
    readonly_stack_manifest_to_dict,
    readonly_stack_manifest_to_markdown,
    summarize_readonly_stack_manifest,
)


class TestBuildReadonlyStackManifest:
    def test_returns_8_components(self):
        manifest = build_readonly_stack_manifest()
        assert len(manifest) == 8

    def test_all_pass(self):
        manifest = build_readonly_stack_manifest()
        assert all(c.status == "PASS" for c in manifest)

    def test_task_ids_t826_to_t833(self):
        manifest = build_readonly_stack_manifest()
        ids = [c.task_id for c in manifest]
        assert ids == ["T826", "T827", "T828", "T829", "T830", "T831", "T832", "T833"]

    def test_deterministic(self):
        a = build_readonly_stack_manifest()
        b = build_readonly_stack_manifest()
        assert a == b

    def test_frozen_dataclass(self):
        manifest = build_readonly_stack_manifest()
        with pytest.raises(AttributeError):
            manifest[0].status = "FAIL"


class TestReadonlyStackManifestToDict:
    def test_returns_list_of_dicts(self):
        manifest = build_readonly_stack_manifest()
        result = readonly_stack_manifest_to_dict(manifest)
        assert isinstance(result, list)
        assert len(result) == 8
        assert all(isinstance(d, dict) for d in result)

    def test_dict_keys(self):
        manifest = build_readonly_stack_manifest()
        result = readonly_stack_manifest_to_dict(manifest)
        expected_keys = {"task_id", "name", "module_path", "test_path", "doc_path", "status"}
        assert all(set(d.keys()) == expected_keys for d in result)

    def test_first_component_values(self):
        manifest = build_readonly_stack_manifest()
        result = readonly_stack_manifest_to_dict(manifest)
        assert result[0]["task_id"] == "T826"
        assert result[0]["status"] == "PASS"


class TestReadonlyStackManifestToMarkdown:
    def test_contains_header(self):
        manifest = build_readonly_stack_manifest()
        md = readonly_stack_manifest_to_markdown(manifest)
        assert "# Runtime Governance Read-Only Stack Manifest" in md

    def test_contains_table_separator(self):
        manifest = build_readonly_stack_manifest()
        md = readonly_stack_manifest_to_markdown(manifest)
        assert "|------|------|--------|------|-----|--------|" in md

    def test_contains_all_tasks(self):
        manifest = build_readonly_stack_manifest()
        md = readonly_stack_manifest_to_markdown(manifest)
        for i in range(826, 834):
            assert f"T{i}" in md

    def test_deterministic(self):
        manifest = build_readonly_stack_manifest()
        assert readonly_stack_manifest_to_markdown(manifest) == readonly_stack_manifest_to_markdown(manifest)


class TestSummarizeReadonlyStackManifest:
    def test_total(self):
        manifest = build_readonly_stack_manifest()
        summary = summarize_readonly_stack_manifest(manifest)
        assert summary["total"] == 8

    def test_pass_count(self):
        manifest = build_readonly_stack_manifest()
        summary = summarize_readonly_stack_manifest(manifest)
        assert summary["pass"] == 8

    def test_fail_count(self):
        manifest = build_readonly_stack_manifest()
        summary = summarize_readonly_stack_manifest(manifest)
        assert summary["fail"] == 0

    def test_all_pass_true(self):
        manifest = build_readonly_stack_manifest()
        summary = summarize_readonly_stack_manifest(manifest)
        assert summary["all_pass"] is True

    def test_task_ids(self):
        manifest = build_readonly_stack_manifest()
        summary = summarize_readonly_stack_manifest(manifest)
        assert summary["task_ids"] == ["T826", "T827", "T828", "T829", "T830", "T831", "T832", "T833"]
