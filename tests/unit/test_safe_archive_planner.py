"""Tests for T25002 — Safe Archive Planner."""
from __future__ import annotations

import json
import pytest

from core.safe_archive_planner import (
    RELEASE_HOLD_REQUIRED_ARC,
    ArchiveAction,
    build_archive_action,
    build_archive_plan,
    compute_archive_hash,
    render_archive_plan_markdown,
)
from core.untracked_runtime_inventory import build_file_record


# --- Build archive plan ---

def test_build_archive_plan_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_archive_plan(release_hold="NOT_HOLD")


def test_archive_plan_empty():
    actions = build_archive_plan()
    assert len(actions) == 0


# --- build_archive_action ---

def test_build_archive_action_fields():
    r = build_file_record("x.py", "ARCHIVE_CANDIDATE", "test reason")
    a = build_archive_action(r)
    assert a.path == "x.py"
    assert a.archive_action == "SIMULATE_ARCHIVE"
    assert a.would_copy is False
    assert a.would_move is False
    assert a.would_delete is False
    assert a.human_approval_required is True
    assert a.simulation_only is True
    assert a.advisory_only is True


def test_action_id_format():
    r = build_file_record("scripts/foo.py", "ARCHIVE_CANDIDATE", "test")
    a = build_archive_action(r)
    assert a.action_id == "arc_scripts__foo_py"


# --- Frozen ---

def test_action_is_frozen():
    r = build_file_record("x.py", "ARCHIVE_CANDIDATE", "test")
    a = build_archive_action(r)
    with pytest.raises(AttributeError):
        a.path = "y.py"


# --- to_dict ---

def test_to_dict_json_serializable():
    r = build_file_record("x.py", "ARCHIVE_CANDIDATE", "test")
    a = build_archive_action(r)
    json.dumps(a.to_dict())


def test_to_dict_keys():
    r = build_file_record("x.py", "ARCHIVE_CANDIDATE", "test")
    a = build_archive_action(r)
    d = a.to_dict()
    assert "action_id" in d
    assert "would_delete" in d
    assert "simulation_only" in d


# --- Hash ---

def test_hash_deterministic():
    actions = build_archive_plan()
    h1 = compute_archive_hash(actions)
    h2 = compute_archive_hash(actions)
    assert h1 == h2


# --- Markdown ---

def test_render_empty_archive_plan():
    actions = build_archive_plan()
    md = render_archive_plan_markdown(actions)
    assert "No archive candidates" in md
    assert "SAFE_*" in md


def test_render_with_actions():
    r = build_file_record("x.py", "ARCHIVE_CANDIDATE", "test")
    a = build_archive_action(r)
    md = render_archive_plan_markdown([a])
    assert "x.py" in md
    assert "SIMULATE_ARCHIVE" in md
    assert "Simulation only:** True" in md
