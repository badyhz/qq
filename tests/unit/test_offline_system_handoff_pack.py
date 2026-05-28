"""Tests for offline system handoff pack.

Verifies:
- required fields present
- safety flags present
- frozen warnings present
- no activation recommendation
- release_hold mismatch fails
- deterministic output
- next-window prompt contains no live/testnet activation instruction
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.offline_system_handoff_pack import (
    RELEASE_HOLD_REQUIRED,
    HandoffPack,
    build_handoff_pack,
    validate_required_fields,
    validate_safety_flags,
    validate_no_activation,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
    write_next_window_prompt,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_pack() -> HandoffPack:
    return build_handoff_pack(repo_root=PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Tests: required fields present
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_no_missing_fields(self):
        pack = _build_pack()
        missing = validate_required_fields(pack)
        assert missing == []

    def test_head_populated(self):
        pack = _build_pack()
        assert pack.current_head
        assert pack.current_head != "unknown"

    def test_stages_populated(self):
        pack = _build_pack()
        assert len(pack.completed_stages) > 0

    def test_safety_populated(self):
        pack = _build_pack()
        assert len(pack.safety_boundaries) > 0

    def test_frozen_list_populated(self):
        pack = _build_pack()
        assert len(pack.frozen_file_list) > 0

    def test_next_prompt_populated(self):
        pack = _build_pack()
        assert len(pack.next_window_prompt) > 0

    def test_no_touch_warning_populated(self):
        pack = _build_pack()
        assert len(pack.no_touch_warning) > 0


# ---------------------------------------------------------------------------
# Tests: safety flags present
# ---------------------------------------------------------------------------

class TestSafetyFlags:
    def test_no_safety_violations(self):
        pack = _build_pack()
        violations = validate_safety_flags(pack)
        assert violations == []

    def test_no_live_flag(self):
        pack = _build_pack()
        assert pack.safety_boundaries.get("no_live") is True

    def test_no_network_flag(self):
        pack = _build_pack()
        assert pack.safety_boundaries.get("no_network") is True

    def test_advisory_only_flag(self):
        pack = _build_pack()
        assert pack.safety_boundaries.get("advisory_only") is True

    def test_human_review_flag(self):
        pack = _build_pack()
        assert pack.safety_boundaries.get("human_review_required") is True


# ---------------------------------------------------------------------------
# Tests: frozen warnings present
# ---------------------------------------------------------------------------

class TestFrozenWarnings:
    def test_no_touch_warning_contains_frozen(self):
        pack = _build_pack()
        assert "frozen" in pack.no_touch_warning.lower()

    def test_frozen_list_not_empty(self):
        pack = _build_pack()
        assert len(pack.frozen_file_list) > 0

    def test_frozen_list_contains_live_runner(self):
        pack = _build_pack()
        assert "core/live_runner.py" in pack.frozen_file_list


# ---------------------------------------------------------------------------
# Tests: no activation recommendation
# ---------------------------------------------------------------------------

class TestNoActivation:
    def test_no_activation_violations(self):
        pack = _build_pack()
        violations = validate_no_activation(pack)
        assert violations == []

    def test_no_live_activation_recommendation_in_prompt(self):
        pack = _build_pack()
        # "activate live" may appear in "do NOT" context (warnings are ok)
        violations = validate_no_activation(pack)
        assert violations == []

    def test_no_testnet_activation_recommendation_in_prompt(self):
        pack = _build_pack()
        violations = validate_no_activation(pack)
        assert violations == []

    def test_dont_list_has_no_activate(self):
        pack = _build_pack()
        for item in pack.what_not_to_do_next:
            lower = item.lower()
            # Items should say "do NOT activate" not "do activate"
            if "activate" in lower:
                assert "not" in lower or "do not" in lower


# ---------------------------------------------------------------------------
# Tests: release_hold mismatch fails
# ---------------------------------------------------------------------------

class TestReleaseHold:
    def test_hold_accepted(self):
        assert validate_release_hold("HOLD") is True

    def test_rejected_values(self):
        for val in ["RELEASED", "", "hold", "HOLD "]:
            assert validate_release_hold(val) is False


# ---------------------------------------------------------------------------
# Tests: deterministic output
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_json_deterministic(self, tmp_path):
        pack = _build_pack()
        p1 = tmp_path / "out1.json"
        p2 = tmp_path / "out2.json"
        write_json(pack, p1)
        write_json(pack, p2)
        assert p1.read_text() == p2.read_text()

    def test_markdown_deterministic(self, tmp_path):
        pack = _build_pack()
        p1 = tmp_path / "out1.md"
        p2 = tmp_path / "out2.md"
        write_markdown(pack, p1)
        write_markdown(pack, p2)
        assert p1.read_text() == p2.read_text()

    def test_next_prompt_deterministic(self, tmp_path):
        pack = _build_pack()
        p1 = tmp_path / "np1.md"
        p2 = tmp_path / "np2.md"
        write_next_window_prompt(pack, p1)
        write_next_window_prompt(pack, p2)
        assert p1.read_text() == p2.read_text()


# ---------------------------------------------------------------------------
# Tests: output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_json_has_all_sections(self, tmp_path):
        pack = _build_pack()
        out = tmp_path / "hp.json"
        write_json(pack, out)
        data = json.loads(out.read_text())
        required = [
            "current_head", "completed_stages", "safety_boundaries",
            "frozen_file_list", "next_window_prompt", "no_touch_warning",
            "command_cheatsheet", "what_to_do_next", "what_not_to_do_next",
            "manifest",
        ]
        for field in required:
            assert field in data, f"Missing: {field}"

    def test_manifest_safety_flags(self):
        pack = _build_pack()
        m = pack.manifest
        assert m["release_hold"] == "HOLD"
        assert m["advisory_only"] is True
        assert m["no_activation_recommendation"] is True

    def test_markdown_contains_sections(self, tmp_path):
        pack = _build_pack()
        out = tmp_path / "hp.md"
        write_markdown(pack, out)
        text = out.read_text()
        assert "Completed Stages" in text
        assert "Safety Boundaries" in text
        assert "What To Do Next" in text
        assert "What NOT To Do Next" in text
        assert "No-Touch Warning" in text
        assert "Command Cheatsheet" in text
