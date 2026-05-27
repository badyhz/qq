"""Tests for release hold dashboard model and renderer.

T1400 — 9+ tests covering frozen dataclass, immutability, hold status, rendering.
"""

import pytest

from core.release_hold_dashboard import ReleaseHoldDashboard
from core.release_hold_dashboard_renderer import (
    render_release_hold_dashboard_md,
    render_hold_status_md,
)


def test_create_dashboard_frozen():
    dash = ReleaseHoldDashboard(
        dashboard_id="D1",
        hold_status="HOLD",
        frozen_count=9,
        medium_count=22,
        governance_layers=("freeze-aware", "untracked-freeze", "frozen-backlog"),
        next_human_action="Review and approve",
    )
    assert dash.dashboard_id == "D1"
    assert dash.frozen_count == 9


def test_dashboard_immutability():
    dash = ReleaseHoldDashboard(
        dashboard_id="D1",
        hold_status="HOLD",
        frozen_count=9,
        medium_count=22,
        governance_layers=(),
        next_human_action="wait",
    )
    with pytest.raises(AttributeError):
        dash.hold_status = "RELEASED"  # type: ignore[misc]


def test_hold_status_is_hold():
    dash = ReleaseHoldDashboard(
        dashboard_id="D1",
        hold_status="HOLD",
        frozen_count=9,
        medium_count=22,
        governance_layers=(),
        next_human_action="wait",
    )
    assert dash.hold_status == "HOLD"


def test_governance_layers_count():
    layers = ("layer1", "layer2", "layer3")
    dash = ReleaseHoldDashboard(
        dashboard_id="D1",
        hold_status="HOLD",
        frozen_count=9,
        medium_count=22,
        governance_layers=layers,
        next_human_action="wait",
    )
    assert len(dash.governance_layers) == 3


def test_governance_layers_tuple():
    layers = ("a", "b")
    dash = ReleaseHoldDashboard(
        dashboard_id="D1",
        hold_status="HOLD",
        frozen_count=0,
        medium_count=0,
        governance_layers=layers,
        next_human_action="wait",
    )
    assert isinstance(dash.governance_layers, tuple)


def test_render_dashboard_md():
    dash = ReleaseHoldDashboard(
        dashboard_id="D1",
        hold_status="HOLD",
        frozen_count=9,
        medium_count=22,
        governance_layers=("freeze-aware", "frozen-backlog"),
        next_human_action="Review",
    )
    md = render_release_hold_dashboard_md(dash)
    assert "D1" in md
    assert "HOLD" in md
    assert "9" in md
    assert "22" in md
    assert "freeze-aware" in md
    assert "Review" in md


def test_render_dashboard_md_empty_layers():
    dash = ReleaseHoldDashboard(
        dashboard_id="D2",
        hold_status="HOLD",
        frozen_count=0,
        medium_count=0,
        governance_layers=(),
        next_human_action="none",
    )
    md = render_release_hold_dashboard_md(dash)
    assert "D2" in md
    assert "HOLD" in md


def test_render_hold_status_md():
    dash = ReleaseHoldDashboard(
        dashboard_id="D1",
        hold_status="HOLD",
        frozen_count=9,
        medium_count=22,
        governance_layers=(),
        next_human_action="wait",
    )
    md = render_hold_status_md(dash)
    assert "HOLD" in md


def test_render_hold_status_md_content():
    dash = ReleaseHoldDashboard(
        dashboard_id="D3",
        hold_status="HOLD",
        frozen_count=5,
        medium_count=10,
        governance_layers=("g1",),
        next_human_action="go",
    )
    md = render_hold_status_md(dash)
    assert md == "**Hold Status:** HOLD"
