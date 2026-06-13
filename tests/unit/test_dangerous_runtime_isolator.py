"""Tests for T25001 — Dangerous Runtime Isolator."""
from __future__ import annotations

import json
import pytest

from core.dangerous_runtime_isolator import (
    ISOLATION_ACTIONS,
    REQUIRED_UNBLOCK_CONDITIONS,
    RELEASE_HOLD_REQUIRED_ISO,
    DenyListEntry,
    build_deny_list_entry,
    build_deny_list,
    compute_deny_list_hash,
    render_deny_list_markdown,
    render_isolation_manifest_markdown,
)
from core.untracked_runtime_inventory import (
    HIGH_RISK_CATEGORIES,
    build_file_record,
    build_inventory,
)


# --- Deny list building ---

def test_build_deny_list_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_deny_list(release_hold="NOT_HOLD")


def test_build_deny_list_returns_high_risk_only():
    entries = build_deny_list()
    for e in entries:
        assert e.risk_category in HIGH_RISK_CATEGORIES


def test_deny_list_count():
    entries = build_deny_list()
    assert len(entries) == 10  # 8 testnet_submit + 1 live + 1 flatten


def test_all_entries_require_human_approval():
    entries = build_deny_list()
    for e in entries:
        assert e.human_approval_required is True


def test_all_entries_no_touch():
    entries = build_deny_list()
    for e in entries:
        assert e.no_touch_required is True


def test_isolation_status_values():
    entries = build_deny_list()
    for e in entries:
        assert e.isolation_status in ("ISOLATED", "QUARANTINED")


def test_no_quarantined_in_current_set():
    entries = build_deny_list()
    quarantined = [e for e in entries if e.isolation_status == "QUARANTINED"]
    assert len(quarantined) == 0  # No HIGH_RISK_SECRET_OR_WEBHOOK in inventory


# --- build_deny_list_entry ---

def test_entry_from_testnet_submit():
    r = build_file_record("x.py", "HIGH_RISK_TESTNET_SUBMIT", "test", has_submit=True)
    e = build_deny_list_entry(r)
    assert e.isolation_status == "ISOLATED"
    assert len(e.isolation_actions) == 4
    assert len(e.required_unblock_conditions) == 3


def test_entry_from_live_runtime():
    r = build_file_record("x.py", "HIGH_RISK_LIVE_RUNTIME", "test", has_submit=True)
    e = build_deny_list_entry(r)
    assert e.isolation_status == "ISOLATED"
    assert len(e.isolation_actions) == 4
    assert len(e.required_unblock_conditions) == 4


def test_entry_from_flatten():
    r = build_file_record("x.py", "HIGH_RISK_FLATTEN", "test", has_submit=True)
    e = build_deny_list_entry(r)
    assert e.isolation_status == "ISOLATED"
    assert len(e.isolation_actions) == 4


def test_entry_from_secret():
    r = build_file_record("x.py", "HIGH_RISK_SECRET_OR_WEBHOOK", "test")
    e = build_deny_list_entry(r)
    assert e.isolation_status == "QUARANTINED"
    assert len(e.isolation_actions) == 4


def test_entry_id_format():
    r = build_file_record("scripts/foo.py", "HIGH_RISK_TESTNET_SUBMIT", "test")
    e = build_deny_list_entry(r)
    assert e.entry_id == "deny_scripts__foo_py"


# --- Hash ---

def test_hash_deterministic():
    entries = build_deny_list()
    h1 = compute_deny_list_hash(entries)
    h2 = compute_deny_list_hash(entries)
    assert h1 == h2


def test_hash_is_sha256():
    entries = build_deny_list()
    h = compute_deny_list_hash(entries)
    assert len(h) == 64


# --- Frozen ---

def test_entry_is_frozen():
    r = build_file_record("x.py", "HIGH_RISK_TESTNET_SUBMIT", "test")
    e = build_deny_list_entry(r)
    with pytest.raises(AttributeError):
        e.path = "y.py"


# --- to_dict ---

def test_to_dict_json_serializable():
    entries = build_deny_list()
    for e in entries:
        d = e.to_dict()
        json.dumps(d)


def test_to_dict_keys():
    r = build_file_record("x.py", "HIGH_RISK_TESTNET_SUBMIT", "test")
    e = build_deny_list_entry(r)
    d = e.to_dict()
    assert "entry_id" in d
    assert "isolation_actions" in d
    assert "required_unblock_conditions" in d


# --- Markdown ---

def test_render_deny_list_has_header():
    entries = build_deny_list()
    md = render_deny_list_markdown(entries)
    assert "# Dangerous Runtime Deny List" in md
    assert "Total isolated files" in md


def test_render_deny_list_has_all_files():
    entries = build_deny_list()
    md = render_deny_list_markdown(entries)
    for e in entries:
        assert e.path in md


def test_render_isolation_manifest_has_table():
    entries = build_deny_list()
    md = render_isolation_manifest_markdown(entries)
    assert "| File | Category |" in md


# --- Isolation actions coverage ---

def test_all_high_risk_categories_have_actions():
    for cat in HIGH_RISK_CATEGORIES:
        assert cat in ISOLATION_ACTIONS
        assert len(ISOLATION_ACTIONS[cat]) >= 3


def test_all_high_risk_categories_have_conditions():
    for cat in HIGH_RISK_CATEGORIES:
        assert cat in REQUIRED_UNBLOCK_CONDITIONS
        assert len(REQUIRED_UNBLOCK_CONDITIONS[cat]) >= 2
