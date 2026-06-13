"""Tests for T30001 — Shadow Pipeline Registry."""
from __future__ import annotations

import json
import pytest

from core.shadow_pipeline_registry import (
    PIPELINE_ROLES,
    PIPELINE_STAGES,
    RELEASE_HOLD_REQUIRED_SPR,
    ShadowPipelineEntry,
    build_pipeline_entry,
    build_shadow_pipeline_registry,
    compute_registry_hash,
    render_registry_markdown,
    render_pipeline_flow_markdown,
)
from core.untracked_runtime_inventory import build_file_record


# --- Build registry ---

def test_build_registry_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_shadow_pipeline_registry(release_hold="NOT_HOLD")


def test_registry_count():
    entries = build_shadow_pipeline_registry()
    assert len(entries) == 4


def test_all_entries_shadow_only():
    entries = build_shadow_pipeline_registry()
    for e in entries:
        assert e.shadow_only is True


def test_all_entries_governance_tracked():
    entries = build_shadow_pipeline_registry()
    for e in entries:
        assert e.governance_tracked is True


def test_all_entries_operator_connected():
    entries = build_shadow_pipeline_registry()
    for e in entries:
        assert e.operator_console_connected is True


# --- build_pipeline_entry ---

def test_build_entry_known_script():
    r = build_file_record("scripts/run_daily_shadow_scan_pipeline.py", "SHADOW_PIPELINE", "test")
    e = build_pipeline_entry(r)
    assert e.pipeline_role == "orchestrator"
    assert e.pipeline_stage == "stage_0_orchestration"


def test_build_entry_unknown_script():
    r = build_file_record("scripts/unknown.py", "SHADOW_PIPELINE", "test")
    e = build_pipeline_entry(r)
    assert e.pipeline_role == "unknown"
    assert e.pipeline_stage == "unknown"


def test_entry_id_format():
    r = build_file_record("scripts/foo.py", "SHADOW_PIPELINE", "test")
    e = build_pipeline_entry(r)
    assert e.entry_id == "spr_scripts__foo_py"


def test_no_submit_default():
    r = build_file_record("x.py", "SHADOW_PIPELINE", "test")
    e = build_pipeline_entry(r)
    assert e.no_submit is True


# --- Frozen ---

def test_entry_is_frozen():
    r = build_file_record("x.py", "SHADOW_PIPELINE", "test")
    e = build_pipeline_entry(r)
    with pytest.raises(AttributeError):
        e.path = "y.py"


# --- to_dict ---

def test_to_dict_json_serializable():
    entries = build_shadow_pipeline_registry()
    for e in entries:
        json.dumps(e.to_dict())


# --- Hash ---

def test_hash_deterministic():
    entries = build_shadow_pipeline_registry()
    h1 = compute_registry_hash(entries)
    h2 = compute_registry_hash(entries)
    assert h1 == h2


def test_hash_is_sha256():
    entries = build_shadow_pipeline_registry()
    h = compute_registry_hash(entries)
    assert len(h) == 64


# --- Markdown ---

def test_render_registry_has_header():
    entries = build_shadow_pipeline_registry()
    md = render_registry_markdown(entries)
    assert "# Shadow Pipeline Registry" in md
    assert "Total pipeline scripts" in md


def test_render_registry_has_all_files():
    entries = build_shadow_pipeline_registry()
    md = render_registry_markdown(entries)
    for e in entries:
        assert e.path in md


def test_render_pipeline_flow():
    entries = build_shadow_pipeline_registry()
    md = render_pipeline_flow_markdown(entries)
    assert "Shadow Pipeline Flow" in md
    assert "orchestrator" in md
    assert "sample_collector" in md


# --- Role/stage coverage ---

def test_all_shadow_pipeline_scripts_have_roles():
    entries = build_shadow_pipeline_registry()
    for e in entries:
        assert e.pipeline_role != "unknown"
        assert e.pipeline_stage != "unknown"


def test_pipeline_stages_ordered():
    entries = build_shadow_pipeline_registry()
    stages = sorted(e.pipeline_stage for e in entries)
    assert stages == ["stage_0_orchestration", "stage_1_backfill", "stage_2_universe", "stage_3_signal_eval"]
