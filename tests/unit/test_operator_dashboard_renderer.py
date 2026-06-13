"""Tests for T39001 — Operator Dashboard Renderer."""
from __future__ import annotations

import json
import pytest

from core.operator_dashboard_renderer import (
    STATUS_COLORS,
    SUBMIT_COLORS,
    HEALTH_COLORS,
    RELEASE_HOLD_REQUIRED_ODR,
    DashboardData,
    build_dashboard_data,
    compute_dashboard_hash,
    render_dashboard_html,
    render_dashboard_markdown,
)


SAMPLE_STATUS = {
    "current_mode": "TESTNET_DRY_RUN_PREP",
    "submit_permission": "NO_SUBMIT",
    "real_submit_allowed": False,
    "testnet_submit_allowed": False,
    "dry_run_allowed": True,
    "frozen_cleanup_status": "COMPLETE",
    "promotion_status": "READY_FOR_TESTNET_DRY_RUN_PREP",
    "strategy_count": 11,
    "active_alert_sources": ["earnings", "stock_price", "macd_rebound", "binance_futures", "system_heartbeat"],
    "critical_blockers": [],
    "next_recommended_phase": "TESTNET_DRY_RUN_SIMULATION",
    "system_healthy": True,
    "dry_run": True,
}


# --- build_dashboard_data ---

def test_build_data_from_status():
    data = build_dashboard_data(SAMPLE_STATUS)
    assert data.current_mode == "TESTNET_DRY_RUN_PREP"
    assert data.submit_permission == "NO_SUBMIT"
    assert data.strategy_count == 11
    assert data.system_healthy is True
    assert data.dry_run is True


def test_build_data_defaults():
    data = build_dashboard_data({})
    assert data.current_mode == "UNKNOWN"
    assert data.submit_permission == "UNKNOWN"
    assert data.real_submit_allowed is False
    assert data.dry_run is True


def test_build_data_with_blockers():
    status = {**SAMPLE_STATUS, "critical_blockers": ["blocker_1", "blocker_2"]}
    data = build_dashboard_data(status)
    assert len(data.critical_blockers) == 2


def test_snapshot_id():
    data = build_dashboard_data(SAMPLE_STATUS, snapshot_id="test_123")
    assert data.snapshot_id == "test_123"


# --- Frozen ---

def test_data_is_frozen():
    data = build_dashboard_data(SAMPLE_STATUS)
    with pytest.raises(AttributeError):
        data.current_mode = "LIVE"


# --- to_dict ---

def test_to_dict_keys():
    data = build_dashboard_data(SAMPLE_STATUS)
    d = data.to_dict()
    assert "current_mode" in d
    assert "active_alert_sources" in d
    assert "critical_blockers" in d
    assert isinstance(d["active_alert_sources"], list)
    assert isinstance(d["critical_blockers"], list)


def test_to_dict_json_serializable():
    data = build_dashboard_data(SAMPLE_STATUS)
    json.dumps(data.to_dict())


# --- Hash ---

def test_hash_deterministic():
    data = build_dashboard_data(SAMPLE_STATUS)
    h1 = compute_dashboard_hash(data)
    h2 = compute_dashboard_hash(data)
    assert h1 == h2


def test_hash_is_sha256():
    data = build_dashboard_data(SAMPLE_STATUS)
    h = compute_dashboard_hash(data)
    assert len(h) == 64


def test_hash_changes_with_data():
    d1 = build_dashboard_data(SAMPLE_STATUS)
    d2 = build_dashboard_data({**SAMPLE_STATUS, "strategy_count": 99})
    assert compute_dashboard_hash(d1) != compute_dashboard_hash(d2)


# --- HTML rendering ---

def test_html_has_title():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "<title>Operator Dashboard</title>" in html


def test_html_has_mode():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "TESTNET_DRY_RUN_PREP" in html


def test_html_has_submit_permission():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "NO_SUBMIT" in html


def test_html_has_strategy_count():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "11" in html


def test_html_has_health_status():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "HEALTHY" in html


def test_html_has_alert_sources():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "earnings" in html
    assert "binance_futures" in html


def test_html_no_blockers():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "None" in html


def test_html_with_blockers():
    status = {**SAMPLE_STATUS, "critical_blockers": ["test_blocker"]}
    data = build_dashboard_data(status)
    html = render_dashboard_html(data)
    assert "test_blocker" in html


def test_html_has_next_phase():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "TESTNET_DRY_RUN_SIMULATION" in html


def test_html_has_dashboard_hash():
    data = build_dashboard_data(SAMPLE_STATUS)
    html = render_dashboard_html(data)
    assert "Dashboard hash:" in html


# --- Markdown rendering ---

def test_markdown_has_header():
    data = build_dashboard_data(SAMPLE_STATUS)
    md = render_dashboard_markdown(data)
    assert "# Operator Dashboard Summary" in md


def test_markdown_has_all_fields():
    data = build_dashboard_data(SAMPLE_STATUS)
    md = render_dashboard_markdown(data)
    assert "TESTNET_DRY_RUN_PREP" in md
    assert "NO_SUBMIT" in md
    assert "HEALTHY" in md
    assert "11" in md


def test_markdown_has_alert_sources():
    data = build_dashboard_data(SAMPLE_STATUS)
    md = render_dashboard_markdown(data)
    for s in data.active_alert_sources:
        assert s in md


# --- Color maps ---

def test_status_colors_coverage():
    assert "TESTNET_DRY_RUN_PREP" in STATUS_COLORS
    assert "SHADOW_ONLY" in STATUS_COLORS
    assert "LIVE" in STATUS_COLORS


def test_submit_colors_coverage():
    assert "NO_SUBMIT" in SUBMIT_COLORS
    assert "TESTNET_SUBMIT" in SUBMIT_COLORS
    assert "LIVE_SUBMIT" in SUBMIT_COLORS
