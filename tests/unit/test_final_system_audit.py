"""Tests for T47001 — Final System Audit."""
from __future__ import annotations

import json
import pytest

from core.final_system_audit import (
    MODULES,
    RELEASE_HOLD_REQUIRED_FSA,
    ModuleAuditEntry,
    SystemAudit,
    build_module_audit,
    build_system_audit,
    compute_audit_hash,
    render_audit_report_markdown,
    render_conclusions_markdown,
)


# --- Module audit ---

def test_build_module_audit_count():
    entries = build_module_audit()
    assert len(entries) == 26


def test_all_modules_complete():
    entries = build_module_audit()
    for e in entries:
        assert e.status == "COMPLETE"


def test_all_modules_governance_tracked():
    entries = build_module_audit()
    for e in entries:
        assert e.governance_tracked is True


def test_all_modules_have_tests():
    entries = build_module_audit()
    for e in entries:
        assert e.tests_exist is True


# --- System audit ---

def test_build_system_audit_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_system_audit(release_hold="NOT_HOLD")


def test_system_audit_totals():
    audit = build_system_audit()
    assert audit.total_modules == 26
    assert audit.completed_modules == 26
    assert audit.all_complete is True


def test_system_audit_safety():
    audit = build_system_audit()
    assert audit.real_submit_blocked is True
    assert audit.dry_run_enforced is True
    assert audit.governance_tracked is True


def test_system_audit_wave_coverage():
    audit = build_system_audit()
    assert "wave_0" in audit.wave_coverage
    assert "wave_1" in audit.wave_coverage
    assert "wave_9" in audit.wave_coverage


# --- Frozen ---

def test_entry_is_frozen():
    entries = build_module_audit()
    with pytest.raises(AttributeError):
        entries[0].module_name = "x"


def test_audit_is_frozen():
    audit = build_system_audit()
    with pytest.raises(AttributeError):
        audit.total_modules = 0


# --- to_dict ---

def test_entry_to_dict_json():
    entries = build_module_audit()
    for e in entries:
        json.dumps(e.to_dict())


def test_audit_to_dict_json():
    audit = build_system_audit()
    json.dumps(audit.to_dict())


# --- Hash ---

def test_hash_deterministic():
    audit = build_system_audit()
    h1 = compute_audit_hash(audit)
    h2 = compute_audit_hash(audit)
    assert h1 == h2


def test_hash_is_sha256():
    audit = build_system_audit()
    h = compute_audit_hash(audit)
    assert len(h) == 64


# --- Markdown ---

def test_render_audit_has_header():
    audit = build_system_audit()
    entries = build_module_audit()
    md = render_audit_report_markdown(audit, entries)
    assert "# Final One-Month System Audit" in md


def test_render_audit_has_all_modules():
    audit = build_system_audit()
    entries = build_module_audit()
    md = render_audit_report_markdown(audit, entries)
    for e in entries:
        assert e.module_name in md


def test_render_conclusions():
    md = render_conclusions_markdown()
    assert "Conclusions" in md
    assert "BLOCKED" in md
    assert "ENFORCED" in md


# --- MODULES constant ---

def test_modules_constant_count():
    assert len(MODULES) == 26


def test_modules_all_have_required_keys():
    for m in MODULES:
        assert "name" in m
        assert "wave" in m
        assert "status" in m
