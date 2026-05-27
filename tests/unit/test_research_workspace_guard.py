"""Tests for research workspace guard — T8481-T8520.

Pre-existing untracked, touched frozen, clean workspace tests.
"""
from __future__ import annotations

import pytest
from core.research_workspace_guard import (
    check_workspace_dirty, check_frozen_file_guard, check_git_add_dot,
)


class TestWorkspaceGuardNormal:
    def test_clean_workspace(self):
        result = check_workspace_dirty((), ())
        assert not result["dirty"]

    def test_clean_frozen_guard(self):
        result = check_frozen_file_guard((), ())
        assert result["clean"]


class TestWorkspaceGuardEdge:
    def test_untracked_dirty(self):
        result = check_workspace_dirty(("file.py",), ())
        assert result["dirty"]

    def test_modified_dirty(self):
        result = check_workspace_dirty((), ("file.py",))
        assert result["dirty"]


class TestWorkspaceGuardAdversarial:
    def test_frozen_violation(self):
        result = check_frozen_file_guard(("core/live_runner.py",), ())
        assert not result["clean"]

    def test_project_state_violation(self):
        result = check_frozen_file_guard((), ("PROJECT_STATE.md",))
        assert not result["clean"]


class TestWorkspaceGuardSafetyBoundary:
    def test_git_add_dot_detection(self):
        many_files = tuple(f"file_{i}.py" for i in range(100))
        assert check_git_add_dot(many_files) is True
