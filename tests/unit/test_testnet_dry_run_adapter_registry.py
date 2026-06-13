"""Tests for T33001 — Testnet Dry-run Adapter Registry."""
from __future__ import annotations

import json
import pytest

from core.testnet_dry_run_adapter_registry import (
    ADAPTER_CONFIGS,
    RELEASE_HOLD_REQUIRED_TDR,
    DryRunAdapterEntry,
    build_adapter_entry,
    build_adapter_registry,
    compute_registry_hash,
    render_registry_markdown,
)
from core.untracked_runtime_inventory import build_file_record


# --- Build registry ---

def test_build_registry_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_adapter_registry(release_hold="NOT_HOLD")


def test_registry_count():
    entries = build_adapter_registry()
    assert len(entries) == 2


def test_all_entries_dry_run_locked():
    entries = build_adapter_registry()
    for e in entries:
        assert e.dry_run_locked is True


def test_all_entries_governance_tracked():
    entries = build_adapter_registry()
    for e in entries:
        assert e.governance_tracked is True


def test_all_entries_no_submit():
    entries = build_adapter_registry()
    for e in entries:
        assert e.no_submit is True


# --- build_adapter_entry ---

def test_build_entry_replay():
    r = build_file_record("scripts/replay_shadow_order_plans_as_testnet_dry.py", "TESTNET_DRY_RUN_ONLY", "test", has_network=True)
    e = build_adapter_entry(r)
    assert e.adapter_type == "dry_run_replay"
    assert e.submit_path == "explicitly_stubbed"


def test_build_entry_diagnostic():
    r = build_file_record("scripts/verify_testnet_repair_scenarios.py", "TESTNET_DRY_RUN_ONLY", "test", has_network=True, has_keys=True, has_adapter=True)
    e = build_adapter_entry(r)
    assert e.adapter_type == "dry_run_diagnostic"
    assert e.submit_path == "force_dry_run_locked"


def test_entry_id_format():
    r = build_file_record("scripts/foo.py", "TESTNET_DRY_RUN_ONLY", "test")
    e = build_adapter_entry(r)
    assert e.entry_id == "tdr_scripts__foo_py"


# --- Frozen ---

def test_entry_is_frozen():
    r = build_file_record("x.py", "TESTNET_DRY_RUN_ONLY", "test")
    e = build_adapter_entry(r)
    with pytest.raises(AttributeError):
        e.path = "y.py"


# --- to_dict ---

def test_to_dict_json_serializable():
    entries = build_adapter_registry()
    for e in entries:
        json.dumps(e.to_dict())


# --- Hash ---

def test_hash_deterministic():
    entries = build_adapter_registry()
    h1 = compute_registry_hash(entries)
    h2 = compute_registry_hash(entries)
    assert h1 == h2


def test_hash_is_sha256():
    entries = build_adapter_registry()
    h = compute_registry_hash(entries)
    assert len(h) == 64


# --- Markdown ---

def test_render_registry_has_header():
    entries = build_adapter_registry()
    md = render_registry_markdown(entries)
    assert "# Testnet Dry-run Adapter Registry" in md
    assert "Total adapters" in md


def test_render_registry_has_all_files():
    entries = build_adapter_registry()
    md = render_registry_markdown(entries)
    for e in entries:
        assert e.path in md


# --- Config coverage ---

def test_all_dry_run_scripts_have_configs():
    entries = build_adapter_registry()
    for e in entries:
        assert e.path in ADAPTER_CONFIGS
