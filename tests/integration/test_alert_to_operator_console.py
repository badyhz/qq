"""Integration test for alert-to-operator-console pipeline."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.runtime_integrations.operator.operator_state_writer import build_runtime_state, write_state


def test_operator_state_includes_alert_count():
    """Operator state reflects alert metrics."""
    state = build_runtime_state(
        research_count=10,
        shadow_signal_count=5,
        shadow_ticker_count=3,
        alert_count=8,
        feishu_payload_count=8,
    )
    assert state.runtime_stats["alert_events"] == 8
    assert state.runtime_stats["research_items"] == 10
    assert state.runtime_stats["shadow_signals"] == 5


def test_operator_state_health_with_blockers():
    """System is unhealthy when blockers exist."""
    state = build_runtime_state(blockers=["test_blocker"])
    assert state.system_healthy is False
    assert "test_blocker" in state.critical_blockers


def test_operator_state_health_without_blockers():
    """System is healthy when no blockers."""
    state = build_runtime_state()
    assert state.system_healthy is True
    assert len(state.critical_blockers) == 0


def test_operator_state_safety_flags():
    """Operator state enforces safety flags."""
    state = build_runtime_state()
    assert state.real_submit_allowed is False
    assert state.testnet_submit_allowed is False
    assert state.dry_run is True
    assert state.submit_permission == "NO_SUBMIT"


def test_operator_state_written_to_file():
    """State is written to JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = pathlib.Path(tmpdir) / "state.json"
        state = build_runtime_state(research_count=42)
        write_state(state, out)
        data = json.loads(out.read_text())
        assert data["runtime_stats"]["research_items"] == 42
        assert data["current_mode"] == "ACTUAL_DRY_RUN"
