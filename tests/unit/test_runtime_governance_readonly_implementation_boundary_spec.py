"""T843: Tests for runtime governance read-only implementation boundary spec."""

import pytest

from core.runtime_governance_readonly_implementation_boundary_spec import (
    RuntimeGovernanceReadOnlyImplementationBoundary,
    build_readonly_implementation_boundary_spec,
    readonly_boundary_spec_to_dict,
    readonly_boundary_spec_to_markdown,
)


class TestBuildReadonlyImplementationBoundarySpec:
    """Tests for build_readonly_implementation_boundary_spec."""

    def test_returns_five_boundaries(self):
        boundaries = build_readonly_implementation_boundary_spec()
        assert len(boundaries) == 5

    def test_all_have_forbidden_patterns(self):
        boundaries = build_readonly_implementation_boundary_spec()
        for b in boundaries:
            assert b.forbidden_file_pattern, f"{b.boundary_id} missing forbidden_file_pattern"
            assert b.forbidden_operation, f"{b.boundary_id} missing forbidden_operation"

    def test_live_runner_forbidden(self):
        boundaries = build_readonly_implementation_boundary_spec()
        core = [b for b in boundaries if b.boundary_id == "core_modules"]
        assert len(core) == 1
        assert "live_runner" in core[0].forbidden_file_pattern

    def test_deterministic(self):
        b1 = build_readonly_implementation_boundary_spec()
        b2 = build_readonly_implementation_boundary_spec()
        assert b1 == b2
        # Verify deep equality via dicts
        assert readonly_boundary_spec_to_dict(b1) == readonly_boundary_spec_to_dict(b2)


class TestReadonlyBoundarySpecToDict:
    """Tests for readonly_boundary_spec_to_dict."""

    def test_returns_list_of_dicts(self):
        boundaries = build_readonly_implementation_boundary_spec()
        result = readonly_boundary_spec_to_dict(boundaries)
        assert isinstance(result, list)
        assert len(result) == 5
        for item in result:
            assert isinstance(item, dict)
            assert "boundary_id" in item
            assert "allowed_file_pattern" in item
            assert "forbidden_file_pattern" in item
            assert "allowed_operation" in item
            assert "forbidden_operation" in item
            assert "notes" in item

    def test_dict_values_match_boundary(self):
        boundaries = build_readonly_implementation_boundary_spec()
        result = readonly_boundary_spec_to_dict(boundaries)
        for orig, d in zip(boundaries, result):
            assert d["boundary_id"] == orig.boundary_id
            assert d["allowed_file_pattern"] == orig.allowed_file_pattern
            assert d["forbidden_file_pattern"] == orig.forbidden_file_pattern
            assert d["allowed_operation"] == orig.allowed_operation
            assert d["forbidden_operation"] == orig.forbidden_operation
            assert d["notes"] == list(orig.notes)


class TestReadonlyBoundarySpecToMarkdown:
    """Tests for readonly_boundary_spec_to_markdown."""

    def test_markdown_contains_boundary_ids(self):
        boundaries = build_readonly_implementation_boundary_spec()
        md = readonly_boundary_spec_to_markdown(boundaries)
        for b in boundaries:
            assert b.boundary_id in md

    def test_markdown_has_table_header(self):
        boundaries = build_readonly_implementation_boundary_spec()
        md = readonly_boundary_spec_to_markdown(boundaries)
        assert "boundary_id" in md
        assert "allowed_file_pattern" in md
        assert "forbidden_file_pattern" in md


class TestFrozenDataclass:
    """Tests for frozen dataclass behavior."""

    def test_boundary_is_frozen(self):
        boundaries = build_readonly_implementation_boundary_spec()
        with pytest.raises(AttributeError):
            boundaries[0].boundary_id = "modified"

    def test_boundary_notes_list_is_shared(self):
        """Frozen dataclass shares the list reference; mutation via list methods is possible
        but the field reference itself is immutable."""
        b = RuntimeGovernanceReadOnlyImplementationBoundary(
            boundary_id="test",
            allowed_file_pattern="*.py",
            forbidden_file_pattern="*.env",
            allowed_operation="read",
            forbidden_operation="write",
            notes=["note1"],
        )
        # Field reassignment blocked
        with pytest.raises(AttributeError):
            b.notes = ["other"]
