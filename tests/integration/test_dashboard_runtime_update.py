"""Integration test for dashboard runtime update."""
from __future__ import annotations

import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.runtime_integrations.operator.operator_state_writer import build_runtime_state
from src.runtime_integrations.operator.dashboard_updater import render_dashboard_html, write_dashboard


def test_dashboard_contains_runtime_stats():
    """Dashboard HTML contains runtime statistics."""
    state = build_runtime_state(
        research_count=42,
        shadow_signal_count=15,
        alert_count=8,
    )
    html = render_dashboard_html(state.to_dict())
    assert "42" in html
    assert "15" in html
    assert "8" in html


def test_dashboard_shows_safety_banners():
    """Dashboard shows safety enforcement banners."""
    state = build_runtime_state()
    html = render_dashboard_html(state.to_dict())
    assert "NOT ALLOWED" in html
    assert "NO_SUBMIT" in html


def test_dashboard_shows_mode():
    """Dashboard shows current mode."""
    state = build_runtime_state()
    html = render_dashboard_html(state.to_dict())
    assert "ACTUAL_DRY_RUN" in html


def test_dashboard_shows_health():
    """Dashboard shows system health."""
    state = build_runtime_state()
    html = render_dashboard_html(state.to_dict())
    assert "HEALTHY" in html

    state_unhealthy = build_runtime_state(blockers=["test"])
    html_unhealthy = render_dashboard_html(state_unhealthy.to_dict())
    assert "UNHEALTHY" in html_unhealthy


def test_dashboard_written_to_file():
    """Dashboard HTML is written to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = pathlib.Path(tmpdir) / "dashboard.html"
        state = build_runtime_state(research_count=99)
        write_dashboard(state.to_dict(), out)
        html = out.read_text()
        assert "99" in html
        assert "Operator Dashboard" in html


def test_dashboard_no_external_cdn():
    """Dashboard has no external CDN references."""
    state = build_runtime_state()
    html = render_dashboard_html(state.to_dict())
    assert "cdn." not in html
    assert "googleapis" not in html
    assert "cloudflare" not in html
