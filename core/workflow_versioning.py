"""Workflow version governance for quantitative trading pipelines."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class VersionCompatibility(Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE_MAJOR = "incompatible_major"
    INCOMPATIBLE_MINOR = "incompatible_minor"
    NOT_FOUND = "not_found"


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""


class WorkflowVersion:
    """Semantic version for workflow governance."""

    def __init__(self, major: int = 1, minor: int = 0, patch: int = 0):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:
        return f"WorkflowVersion({self.major}, {self.minor}, {self.patch})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkflowVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: WorkflowVersion) -> bool:
        if not isinstance(other, WorkflowVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: WorkflowVersion) -> bool:
        if not isinstance(other, WorkflowVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: WorkflowVersion) -> bool:
        if not isinstance(other, WorkflowVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: WorkflowVersion) -> bool:
        if not isinstance(other, WorkflowVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def is_compatible(self, other: WorkflowVersion) -> bool:
        """Same major version = compatible."""
        return self.major == other.major

    def to_dict(self) -> dict:
        return {"major": self.major, "minor": self.minor, "patch": self.patch}

    @classmethod
    def from_dict(cls, d: dict) -> WorkflowVersion:
        return cls(major=d["major"], minor=d["minor"], patch=d["patch"])


class WorkflowVersionRegistry:
    """Registry for workflow versions with schema validation."""

    def __init__(self):
        self._workflows: dict[str, dict] = {}  # name -> {version, schema, history}

    def register(
        self,
        workflow_name: str,
        version: WorkflowVersion,
        schema: dict = None,
    ) -> None:
        if workflow_name not in self._workflows:
            self._workflows[workflow_name] = {"history": []}

        entry = self._workflows[workflow_name]
        entry["version"] = version
        entry["schema"] = schema
        entry["history"].append(version)

    def get_version(self, workflow_name: str) -> Optional[WorkflowVersion]:
        entry = self._workflows.get(workflow_name)
        if entry is None:
            return None
        return entry["version"]

    def check_compatibility(
        self,
        workflow_name: str,
        required_version: WorkflowVersion,
    ) -> VersionCompatibility:
        version = self.get_version(workflow_name)
        if version is None:
            return VersionCompatibility.NOT_FOUND

        if version.major != required_version.major:
            return VersionCompatibility.INCOMPATIBLE_MAJOR

        if version.minor < required_version.minor:
            return VersionCompatibility.INCOMPATIBLE_MINOR

        return VersionCompatibility.COMPATIBLE

    def list_workflows(self) -> dict[str, str]:
        return {name: str(entry["version"]) for name, entry in self._workflows.items()}

    def get_schema(self, workflow_name: str) -> Optional[dict]:
        entry = self._workflows.get(workflow_name)
        if entry is None:
            return None
        return entry.get("schema")

    def validate_schema(
        self,
        workflow_name: str,
        actual_tasks: list[dict],
    ) -> list[str]:
        errors: list[str] = []
        schema = self.get_schema(workflow_name)
        if schema is None:
            return errors

        # Check required fields
        required_fields = schema.get("required_fields", [])
        for i, task in enumerate(actual_tasks):
            for field in required_fields:
                if field not in task:
                    errors.append(f"Task {i}: missing required field '{field}'")

        # Check task count
        expected_count = schema.get("task_count")
        if expected_count is not None and len(actual_tasks) != expected_count:
            errors.append(
                f"Task count mismatch: expected {expected_count}, got {len(actual_tasks)}"
            )

        # Check dependency validity
        valid_ids = {task.get("id") for task in actual_tasks if "id" in task}
        for i, task in enumerate(actual_tasks):
            deps = task.get("dependencies", [])
            for dep in deps:
                if dep not in valid_ids:
                    errors.append(f"Task {i}: invalid dependency '{dep}'")

        if errors:
            raise SchemaValidationError("; ".join(errors))

        return errors

    def summary(self) -> dict:
        return {
            "total_workflows": len(self._workflows),
            "workflows": {
                name: {
                    "version": str(entry["version"]),
                    "has_schema": entry.get("schema") is not None,
                    "version_count": len(entry["history"]),
                }
                for name, entry in self._workflows.items()
            },
        }
