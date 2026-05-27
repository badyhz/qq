"""Tests for dev PRD control plane documents.

Deterministic. No I/O. No network. No timestamps.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd"

REQUIRED_DOCS = [
    "agent_execution_protocol.md",
    "runtime_governance_prd.md",
    "runtime_governance_safety_boundaries.md",
    "runtime_governance_task_queue.md",
    "runtime_governance_acceptance.md",
    "runtime_governance_current_state.md",
    "runtime_governance_future_phases.md",
]


def _read_doc(name: str) -> str:
    return (DOCS_DIR / name).read_text(encoding="utf-8")


# ── existence ──────────────────────────────────────────────────────────


class TestDocsExist:
    def test_all_7_docs_exist(self):
        for name in REQUIRED_DOCS:
            assert (DOCS_DIR / name).exists(), f"Missing: {name}"


# ── agent_execution_protocol ───────────────────────────────────────────


class TestAgentExecutionProtocol:
    def test_contains_output_format(self):
        text = _read_doc("agent_execution_protocol.md")
        for field in ["FILES", "TESTS", "COMMITS", "RESULT", "NOTES"]:
            assert field in text, f"Missing {field}"

    def test_contains_api_freeze(self):
        text = _read_doc("agent_execution_protocol.md")
        assert "API freeze" in text.lower() or "api freeze" in text.lower()

    def test_contains_stop_conditions(self):
        text = _read_doc("agent_execution_protocol.md")
        assert "stop condition" in text.lower() or "stop conditions" in text.lower()


# ── safety_boundaries ──────────────────────────────────────────────────


class TestSafetyBoundaries:
    def test_contains_frozen_items(self):
        text = _read_doc("runtime_governance_safety_boundaries.md")
        for item in ["live trading", "order submission", "secrets", "planner integration", "account state mutation"]:
            assert item in text.lower(), f"Missing: {item}"


# ── task_queue ─────────────────────────────────────────────────────────


class TestTaskQueue:
    def test_contains_completed_ranges(self):
        text = _read_doc("runtime_governance_task_queue.md")
        for rng in ["T786-T789", "T798-T825", "T826-T857"]:
            assert rng in text, f"Missing: {rng}"

    def test_contains_future_tasks(self):
        text = _read_doc("runtime_governance_task_queue.md")
        assert "T865" in text
        assert "HUMAN_REVIEW_REQUIRED" in text


# ── acceptance ─────────────────────────────────────────────────────────


class TestAcceptance:
    def test_contains_result_definitions(self):
        text = _read_doc("runtime_governance_acceptance.md")
        for result in ["PASS", "PARTIAL", "FAIL", "BLOCKED"]:
            assert result in text, f"Missing: {result}"

    def test_contains_pytest(self):
        text = _read_doc("runtime_governance_acceptance.md")
        assert "pytest" in text


# ── current_state ──────────────────────────────────────────────────────


class TestCurrentState:
    def test_contains_test_counts(self):
        text = _read_doc("runtime_governance_current_state.md")
        assert "778 passed" in text
        assert "308 passed" in text
        assert "140 passed" in text


# ── future_phases ──────────────────────────────────────────────────────


class TestFuturePhases:
    def test_no_live_authorization(self):
        text = _read_doc("runtime_governance_future_phases.md")
        assert "no current document authorizes live trading" in text.lower()

    def test_requires_human_instruction(self):
        text = _read_doc("runtime_governance_future_phases.md")
        assert "human/manual instruction" in text or "human instruction" in text


# ── no unauthorized live claims ────────────────────────────────────────


class TestNoUnauthorizedClaims:
    def test_no_authorized_for_live(self):
        for name in REQUIRED_DOCS:
            text = _read_doc(name)
            assert "authorized for live trading" not in text.lower(), f"{name} contains unauthorized claim"

    def test_no_authorized_for_real_order(self):
        for name in REQUIRED_DOCS:
            text = _read_doc(name)
            assert "authorized for real order placement" not in text.lower(), f"{name} contains unauthorized claim"
