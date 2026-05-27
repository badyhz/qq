"""Tests for runtime governance preflight renderer."""

from __future__ import annotations

import re

from core.runtime_governance_contract import (
    RuntimeGovernanceInput,
    validate_runtime_governance_input,
)
from core.runtime_governance_dry_run_adapter import (
    RuntimeGovernanceDryRunResult,
    evaluate_runtime_governance_dry_run,
)
from core.runtime_governance_audit_event import (
    build_runtime_governance_audit_event,
)
from core.runtime_governance_preflight_packet import (
    RuntimeGovernancePreflightPacket,
    build_runtime_governance_preflight_packet,
)
from core.runtime_governance_preflight_renderer import (
    render_preflight_summary,
    render_preflight_markdown,
    render_preflight_compact_dict,
)


def _make_pass_packet() -> RuntimeGovernancePreflightPacket:
    """Build a packet that passes all checks."""
    inp = RuntimeGovernanceInput(
        run_id="run-001",
        adapter_id="adapt-001",
        mode="shadow",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
    )
    return build_runtime_governance_preflight_packet(inp)


def _make_fail_packet() -> RuntimeGovernancePreflightPacket:
    """Build a packet with failures (CRITICAL policy block)."""
    inp = RuntimeGovernanceInput(
        run_id="run-002",
        adapter_id="adapt-002",
        mode="shadow",
        requested_action="submit",
        symbol="BTCUSDT",
        environment="production",
        allow_network=True,
        allow_submit=True,
        allow_file_io=False,
    )
    return build_runtime_governance_preflight_packet(inp)


def _make_invalid_packet() -> RuntimeGovernancePreflightPacket:
    """Build a packet with validation failures (empty run_id, bad mode)."""
    inp = RuntimeGovernanceInput(
        run_id="",
        adapter_id="",
        mode="bad_mode",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
    )
    return build_runtime_governance_preflight_packet(inp)


def test_pass_packet_ready_true():
    packet = _make_pass_packet()
    summary = render_preflight_summary(packet)
    assert summary["ready"] is True
    assert summary["proceed"] is True
    assert summary["final_verdict"] == "PASS"
    assert summary["blocker_count"] == 0
    assert summary["failure_count"] == 0


def test_invalid_packet_ready_false_with_blockers():
    packet = _make_invalid_packet()
    summary = render_preflight_summary(packet)
    assert summary["ready"] is False
    assert summary["proceed"] is False
    assert summary["blocker_count"] > 0
    assert summary["failure_count"] > 0


def test_blocked_packet_shows_blockers():
    packet = _make_fail_packet()
    md = render_preflight_markdown(packet)
    assert "## Blockers" in md
    # CRITICAL policy blocks should appear
    assert "policy_block" in md
    assert "critical" in md


def test_compact_dict_has_expected_keys():
    packet = _make_pass_packet()
    compact = render_preflight_compact_dict(packet)
    expected_keys = {"verdict", "proceed", "failures"}
    assert set(compact.keys()) == expected_keys
    assert compact["verdict"] == "PASS"
    assert compact["proceed"] is True
    assert compact["failures"] == 0


def test_markdown_deterministic():
    packet = _make_fail_packet()
    md1 = render_preflight_markdown(packet)
    md2 = render_preflight_markdown(packet)
    assert md1 == md2


def test_markdown_contains_expected_sections():
    packet = _make_pass_packet()
    md = render_preflight_markdown(packet)
    assert "# Runtime Governance Preflight" in md
    assert "## Final Verdict" in md
    assert "## Ready For Runtime" in md
    assert "## Blockers" in md
    assert "## Failures" in md
    assert "## Audit Event" in md
    assert "## Notes" in md


def test_markdown_no_timestamps():
    packet = _make_fail_packet()
    md = render_preflight_markdown(packet)
    # no ISO timestamps, no "202" year strings
    assert not re.search(r"\d{4}-\d{2}-\d{2}", md)
    assert not re.search(r"\d{2}:\d{2}:\d{2}", md)
