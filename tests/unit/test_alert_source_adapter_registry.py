"""Tests for T36001 — Alert Source Adapter Registry."""
from __future__ import annotations

import json
import pytest

from core.alert_source_adapter_registry import (
    ALERT_SOURCES,
    SOURCE_CONFIGS,
    RELEASE_HOLD_REQUIRED_ASR,
    AlertSourceAdapter,
    build_adapter,
    build_adapter_registry,
    compute_registry_hash,
    render_registry_markdown,
    render_integration_matrix_markdown,
)


# --- Build registry ---

def test_build_registry_requires_hold():
    with pytest.raises(ValueError, match="HOLD"):
        build_adapter_registry(release_hold="NOT_HOLD")


def test_registry_count():
    adapters = build_adapter_registry()
    assert len(adapters) == 5


def test_all_adapters_integrated():
    adapters = build_adapter_registry()
    for a in adapters:
        assert a.integrated_with_alert_center is True


def test_all_adapters_dry_run_compatible():
    adapters = build_adapter_registry()
    for a in adapters:
        assert a.dry_run_compatible is True


def test_all_adapters_governance_tracked():
    adapters = build_adapter_registry()
    for a in adapters:
        assert a.governance_tracked is True


# --- build_adapter ---

def test_build_adapter_earnings():
    a = build_adapter("earnings")
    assert a.adapter_type == "event_driven"
    assert a.priority == "HIGH"
    assert a.network_required is False


def test_build_adapter_binance_futures():
    a = build_adapter("binance_futures")
    assert a.adapter_type == "market_scanner"
    assert a.priority == "HIGH"
    assert a.network_required is True


def test_build_adapter_system_heartbeat():
    a = build_adapter("system_heartbeat")
    assert a.adapter_type == "health_monitor"
    assert a.priority == "LOW"


def test_adapter_id_format():
    a = build_adapter("earnings")
    assert a.adapter_id == "asr_earnings"


# --- Frozen ---

def test_adapter_is_frozen():
    a = build_adapter("earnings")
    with pytest.raises(AttributeError):
        a.source_name = "x"


# --- to_dict ---

def test_to_dict_json_serializable():
    adapters = build_adapter_registry()
    for a in adapters:
        json.dumps(a.to_dict())


# --- Hash ---

def test_hash_deterministic():
    adapters = build_adapter_registry()
    h1 = compute_registry_hash(adapters)
    h2 = compute_registry_hash(adapters)
    assert h1 == h2


def test_hash_is_sha256():
    adapters = build_adapter_registry()
    h = compute_registry_hash(adapters)
    assert len(h) == 64


# --- Markdown ---

def test_render_registry_has_header():
    adapters = build_adapter_registry()
    md = render_registry_markdown(adapters)
    assert "# Alert Source Adapter Registry" in md
    assert "Total adapters" in md


def test_render_registry_has_all_sources():
    adapters = build_adapter_registry()
    md = render_registry_markdown(adapters)
    for a in adapters:
        assert a.source_name in md


def test_render_integration_matrix_has_table():
    adapters = build_adapter_registry()
    md = render_integration_matrix_markdown(adapters)
    assert "| Source | Type |" in md
    lines = [l for l in md.split("\n") if l.startswith("|") and not l.startswith("| Source") and not l.startswith("|---")]
    assert len(lines) == 5


# --- Config coverage ---

def test_all_sources_have_configs():
    for s in ALERT_SOURCES:
        assert s in SOURCE_CONFIGS
        assert "adapter_type" in SOURCE_CONFIGS[s]
        assert "priority" in SOURCE_CONFIGS[s]
