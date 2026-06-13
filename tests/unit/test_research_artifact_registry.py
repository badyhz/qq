"""Tests for T27001 — Research Artifact Registry."""
from __future__ import annotations

import json
import pytest

from core.research_artifact_registry import (
    SAFE_CATEGORIES,
    ARTIFACT_TYPES,
    INTEGRATION_PATHS,
    RELEASE_HOLD_REQUIRED_REG,
    ResearchArtifact,
    build_artifact,
    build_artifact_registry,
    compute_registry_hash,
    render_registry_markdown,
    render_integration_matrix_markdown,
)
from core.untracked_runtime_inventory import build_file_record


# --- Build registry ---

def test_build_registry_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_artifact_registry(release_hold="NOT_HOLD")


def test_registry_contains_only_safe():
    artifacts = build_artifact_registry()
    for a in artifacts:
        assert a.risk_category in SAFE_CATEGORIES


def test_registry_count():
    artifacts = build_artifact_registry()
    # 8 SAFE_RESEARCH + 2 SAFE_IMPORTER + 1 SAFE_REPORT = 11
    assert len(artifacts) == 11


def test_registry_by_type():
    artifacts = build_artifact_registry()
    by_type = {}
    for a in artifacts:
        by_type.setdefault(a.artifact_type, []).append(a)
    assert len(by_type.get("research_scanner", [])) == 8
    assert len(by_type.get("data_source_adapter", [])) == 2
    assert len(by_type.get("verification_report", [])) == 1


# --- build_artifact ---

def test_build_artifact_research():
    r = build_file_record("x.py", "SAFE_RESEARCH", "test")
    a = build_artifact(r)
    assert a.artifact_type == "research_scanner"
    assert a.integration_target == "strategy_registry"
    assert a.governance_tracked is True
    assert a.ready_for_integration is True


def test_build_artifact_importer():
    r = build_file_record("x.py", "SAFE_IMPORTER", "test")
    a = build_artifact(r)
    assert a.artifact_type == "data_source_adapter"
    assert a.integration_target == "alert_center"


def test_build_artifact_report():
    r = build_file_record("x.py", "SAFE_REPORT", "test")
    a = build_artifact(r)
    assert a.artifact_type == "verification_report"
    assert a.integration_target == "operator_console"


def test_artifact_id_format():
    r = build_file_record("scripts/foo.py", "SAFE_RESEARCH", "test")
    a = build_artifact(r)
    assert a.artifact_id == "art_scripts__foo_py"


def test_dry_run_compatible_no_network():
    r = build_file_record("x.py", "SAFE_RESEARCH", "test")
    a = build_artifact(r)
    assert a.dry_run_compatible is True


def test_dry_run_compatible_with_network():
    r = build_file_record("x.py", "SAFE_IMPORTER", "test", has_network=True)
    a = build_artifact(r)
    assert a.dry_run_compatible is False


# --- Frozen ---

def test_artifact_is_frozen():
    r = build_file_record("x.py", "SAFE_RESEARCH", "test")
    a = build_artifact(r)
    with pytest.raises(AttributeError):
        a.path = "y.py"


# --- to_dict ---

def test_to_dict_json_serializable():
    r = build_file_record("x.py", "SAFE_RESEARCH", "test")
    a = build_artifact(r)
    json.dumps(a.to_dict())


# --- Hash ---

def test_hash_deterministic():
    artifacts = build_artifact_registry()
    h1 = compute_registry_hash(artifacts)
    h2 = compute_registry_hash(artifacts)
    assert h1 == h2


def test_hash_is_sha256():
    artifacts = build_artifact_registry()
    h = compute_registry_hash(artifacts)
    assert len(h) == 64


# --- Markdown ---

def test_render_registry_has_header():
    artifacts = build_artifact_registry()
    md = render_registry_markdown(artifacts)
    assert "# Research Artifact Registry" in md
    assert "Total artifacts" in md


def test_render_registry_has_all_files():
    artifacts = build_artifact_registry()
    md = render_registry_markdown(artifacts)
    for a in artifacts:
        assert a.path in md


def test_render_integration_matrix_has_table():
    artifacts = build_artifact_registry()
    md = render_integration_matrix_markdown(artifacts)
    assert "| File | Type |" in md
    lines = [l for l in md.split("\n") if l.startswith("|") and not l.startswith("| File") and not l.startswith("|---")]
    assert len(lines) == 11


# --- Coverage ---

def test_all_safe_categories_have_types():
    for cat in SAFE_CATEGORIES:
        assert cat in ARTIFACT_TYPES


def test_all_safe_categories_have_targets():
    for cat in SAFE_CATEGORIES:
        assert cat in INTEGRATION_PATHS
