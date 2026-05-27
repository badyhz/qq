"""T1891-T1900 - Tests for frozen backlog agent handoff generator."""
from __future__ import annotations

import os
import sys

import pytest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.frozen_backlog_agent_handoff_generator import generate_agent_handoff
from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY
from core.frozen_backlog_report_materializer import materialize_report_summary


@pytest.fixture()
def handoff_output():
    inventory = FROZEN_BACKLOG_INVENTORY
    summary = materialize_report_summary(inventory)
    return generate_agent_handoff(inventory, summary)


class TestAgentHandoffGenerator:
    def test_output_contains_all_22_frozen_file_paths(self, handoff_output):
        for rec in FROZEN_BACKLOG_INVENTORY.records:
            assert rec.file_path in handoff_output, (
                f"Missing frozen file path: {rec.file_path}"
            )

    def test_output_contains_hold(self, handoff_output):
        assert "HOLD" in handoff_output
        assert "release_hold = HOLD" in handoff_output

    def test_output_contains_forbidden_path_warnings(self, handoff_output):
        assert "Forbidden" in handoff_output
        assert "DO NOT MODIFY" in handoff_output
        assert "MUST NOT modify" in handoff_output

    def test_output_contains_commit_rules(self, handoff_output):
        assert "Commit Rules" in handoff_output
        assert "explicit `git add" in handoff_output
        assert "NEVER use `git add .`" in handoff_output

    def test_output_contains_allowed_scope(self, handoff_output):
        assert "Allowed Scope" in handoff_output
        assert "core/*" in handoff_output
        assert "scripts/*" in handoff_output
        assert "docs/dev_prd/*" in handoff_output
        assert "tests/*" in handoff_output

    def test_deterministic_same_input_same_output(self):
        inventory = FROZEN_BACKLOG_INVENTORY
        summary = materialize_report_summary(inventory)
        out1 = generate_agent_handoff(inventory, summary)
        out2 = generate_agent_handoff(inventory, summary)
        assert out1 == out2

    def test_output_contains_safety_warnings(self, handoff_output):
        assert "no_live" in handoff_output
        assert "no_submit" in handoff_output
        assert "no_exchange" in handoff_output
        assert "Do NOT import" in handoff_output
        assert "Do NOT make network calls" in handoff_output
