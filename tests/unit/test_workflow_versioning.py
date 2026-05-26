"""Unit tests for workflow versioning module."""

import pytest

from core.workflow_versioning import (
    SchemaValidationError,
    VersionCompatibility,
    WorkflowVersion,
    WorkflowVersionRegistry,
)


# --- Version creation and string ---

class TestWorkflowVersion:
    def test_default_version(self):
        v = WorkflowVersion()
        assert str(v) == "1.0.0"

    def test_custom_version(self):
        v = WorkflowVersion(2, 3, 4)
        assert str(v) == "2.3.4"

    def test_repr(self):
        v = WorkflowVersion(1, 2, 3)
        assert repr(v) == "WorkflowVersion(1, 2, 3)"

    # --- Comparison operators ---

    def test_eq(self):
        assert WorkflowVersion(1, 0, 0) == WorkflowVersion(1, 0, 0)

    def test_ne(self):
        assert WorkflowVersion(1, 0, 0) != WorkflowVersion(1, 1, 0)

    def test_lt(self):
        assert WorkflowVersion(1, 0, 0) < WorkflowVersion(1, 1, 0)
        assert WorkflowVersion(1, 0, 0) < WorkflowVersion(2, 0, 0)

    def test_le(self):
        assert WorkflowVersion(1, 0, 0) <= WorkflowVersion(1, 0, 0)
        assert WorkflowVersion(1, 0, 0) <= WorkflowVersion(1, 0, 1)

    def test_gt(self):
        assert WorkflowVersion(1, 1, 0) > WorkflowVersion(1, 0, 0)

    def test_ge(self):
        assert WorkflowVersion(1, 0, 0) >= WorkflowVersion(1, 0, 0)
        assert WorkflowVersion(2, 0, 0) >= WorkflowVersion(1, 0, 0)

    # --- Compatibility ---

    def test_compatible_same_major(self):
        a = WorkflowVersion(1, 0, 0)
        b = WorkflowVersion(1, 5, 3)
        assert a.is_compatible(b) is True
        assert b.is_compatible(a) is True

    def test_incompatible_different_major(self):
        a = WorkflowVersion(1, 0, 0)
        b = WorkflowVersion(2, 0, 0)
        assert a.is_compatible(b) is False

    # --- Dict round-trip ---

    def test_to_dict(self):
        v = WorkflowVersion(3, 2, 1)
        d = v.to_dict()
        assert d == {"major": 3, "minor": 2, "patch": 1}

    def test_from_dict(self):
        d = {"major": 3, "minor": 2, "patch": 1}
        v = WorkflowVersion.from_dict(d)
        assert v == WorkflowVersion(3, 2, 1)

    def test_from_dict_round_trip(self):
        original = WorkflowVersion(5, 4, 3)
        restored = WorkflowVersion.from_dict(original.to_dict())
        assert original == restored


# --- Registry ---

class TestWorkflowVersionRegistry:
    def test_register_and_get(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(1, 0, 0))
        assert reg.get_version("alpha") == WorkflowVersion(1, 0, 0)

    def test_get_nonexistent(self):
        reg = WorkflowVersionRegistry()
        assert reg.get_version("ghost") is None

    def test_list_workflows(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(1, 0, 0))
        reg.register("beta", WorkflowVersion(2, 1, 0))
        result = reg.list_workflows()
        assert result == {"alpha": "1.0.0", "beta": "2.1.0"}

    def test_multiple_versions_same_workflow(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(1, 0, 0))
        reg.register("alpha", WorkflowVersion(1, 1, 0))
        assert reg.get_version("alpha") == WorkflowVersion(1, 1, 0)

    def test_summary(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(1, 0, 0))
        s = reg.summary()
        assert s["total_workflows"] == 1
        assert "alpha" in s["workflows"]
        assert s["workflows"]["alpha"]["version"] == "1.0.0"
        assert s["workflows"]["alpha"]["version_count"] == 1

    # --- Compatibility checks ---

    def test_compatibility_compatible(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(1, 2, 0))
        result = reg.check_compatibility("alpha", WorkflowVersion(1, 0, 0))
        assert result == VersionCompatibility.COMPATIBLE

    def test_compatibility_incompatible_major(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(2, 0, 0))
        result = reg.check_compatibility("alpha", WorkflowVersion(1, 0, 0))
        assert result == VersionCompatibility.INCOMPATIBLE_MAJOR

    def test_compatibility_incompatible_minor(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(1, 1, 0))
        result = reg.check_compatibility("alpha", WorkflowVersion(1, 3, 0))
        assert result == VersionCompatibility.INCOMPATIBLE_MINOR

    def test_compatibility_not_found(self):
        reg = WorkflowVersionRegistry()
        result = reg.check_compatibility("ghost", WorkflowVersion(1, 0, 0))
        assert result == VersionCompatibility.NOT_FOUND

    # --- Schema ---

    def test_get_schema(self):
        reg = WorkflowVersionRegistry()
        schema = {"required_fields": ["id", "name"], "task_count": 3}
        reg.register("alpha", WorkflowVersion(1, 0, 0), schema=schema)
        assert reg.get_schema("alpha") == schema

    def test_get_schema_nonexistent(self):
        reg = WorkflowVersionRegistry()
        assert reg.get_schema("ghost") is None

    def test_validate_schema_valid(self):
        reg = WorkflowVersionRegistry()
        schema = {"required_fields": ["id"], "task_count": 2}
        reg.register("alpha", WorkflowVersion(1, 0, 0), schema=schema)
        tasks = [
            {"id": "t1", "dependencies": []},
            {"id": "t2", "dependencies": ["t1"]},
        ]
        errors = reg.validate_schema("alpha", tasks)
        assert errors == []

    def test_validate_schema_missing_id(self):
        reg = WorkflowVersionRegistry()
        schema = {"required_fields": ["id"]}
        reg.register("alpha", WorkflowVersion(1, 0, 0), schema=schema)
        tasks = [{"dependencies": []}]
        with pytest.raises(SchemaValidationError, match="missing required field 'id'"):
            reg.validate_schema("alpha", tasks)

    def test_validate_schema_invalid_dep(self):
        reg = WorkflowVersionRegistry()
        schema = {"required_fields": ["id"]}
        reg.register("alpha", WorkflowVersion(1, 0, 0), schema=schema)
        tasks = [
            {"id": "t1", "dependencies": ["nonexistent"]},
        ]
        with pytest.raises(SchemaValidationError, match="invalid dependency"):
            reg.validate_schema("alpha", tasks)

    def test_validate_schema_task_count_mismatch(self):
        reg = WorkflowVersionRegistry()
        schema = {"required_fields": ["id"], "task_count": 5}
        reg.register("alpha", WorkflowVersion(1, 0, 0), schema=schema)
        tasks = [{"id": "t1"}, {"id": "t2"}]
        with pytest.raises(SchemaValidationError, match="Task count mismatch"):
            reg.validate_schema("alpha", tasks)

    def test_validate_no_schema_returns_empty(self):
        reg = WorkflowVersionRegistry()
        reg.register("alpha", WorkflowVersion(1, 0, 0))
        errors = reg.validate_schema("alpha", [{"id": "t1"}])
        assert errors == []
