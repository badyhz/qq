"""Tests for core.runtime_governance_sample_factory.

Deterministic. No I/O. No network. No random. No timestamps.
"""

import pytest

from core.runtime_governance_contract import RuntimeGovernanceInput
from core.runtime_governance_preflight_packet import RuntimeGovernancePreflightPacket
from core.runtime_governance_sample_factory import (
    build_runtime_governance_sample_input,
    build_runtime_governance_sample_markdown,
    build_runtime_governance_sample_preflight_packet,
)


ALL_KINDS = ["pass", "fail", "blocked", "warn_like", "invalid_contract"]


# ── each kind builds without error ────────────────────────────────────


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_build_input_no_error(kind: str):
    result = build_runtime_governance_sample_input(kind)
    assert isinstance(result, RuntimeGovernanceInput)


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_build_preflight_packet_no_error(kind: str):
    result = build_runtime_governance_sample_preflight_packet(kind)
    assert isinstance(result, RuntimeGovernancePreflightPacket)


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_build_markdown_no_error(kind: str):
    result = build_runtime_governance_sample_markdown(kind)
    assert isinstance(result, str)
    assert len(result) > 0


# ── pass kind → ready=True ────────────────────────────────────────────


def test_pass_kind_ready_true():
    packet = build_runtime_governance_sample_preflight_packet("pass")
    assert packet.proceed is True
    assert packet.final_verdict == "PASS"


# ── fail kind → ready=False ───────────────────────────────────────────


def test_fail_kind_ready_false():
    packet = build_runtime_governance_sample_preflight_packet("fail")
    assert packet.proceed is False
    assert packet.final_verdict == "FAIL"


# ── blocked kind → has blockers ───────────────────────────────────────


def test_blocked_kind_has_blockers():
    packet = build_runtime_governance_sample_preflight_packet("blocked")
    assert packet.proceed is False
    assert packet.final_verdict == "BLOCKED"
    assert packet.dry_run_result.contract_result.ok is False
    assert len(packet.dry_run_result.contract_result.failures) > 0


# ── unsupported kind raises ValueError ────────────────────────────────


def test_unsupported_kind_raises():
    with pytest.raises(ValueError, match="unsupported sample kind"):
        build_runtime_governance_sample_input("no_such_kind")


def test_unsupported_kind_raises_preflight():
    with pytest.raises(ValueError, match="unsupported sample kind"):
        build_runtime_governance_sample_preflight_packet("no_such_kind")


def test_unsupported_kind_raises_markdown():
    with pytest.raises(ValueError, match="unsupported sample kind"):
        build_runtime_governance_sample_markdown("no_such_kind")


# ── determinism: repeated outputs identical ────────────────────────────


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_input_determinism(kind: str):
    a = build_runtime_governance_sample_input(kind)
    b = build_runtime_governance_sample_input(kind)
    assert a == b


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_preflight_packet_determinism(kind: str):
    a = build_runtime_governance_sample_preflight_packet(kind)
    b = build_runtime_governance_sample_preflight_packet(kind)
    assert a.final_verdict == b.final_verdict
    assert a.proceed == b.proceed
    assert a.input == b.input


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_markdown_determinism(kind: str):
    a = build_runtime_governance_sample_markdown(kind)
    b = build_runtime_governance_sample_markdown(kind)
    assert a == b


# ── warn_like kind specifics ──────────────────────────────────────────


def test_warn_like_kind_pass_verdict():
    packet = build_runtime_governance_sample_preflight_packet("warn_like")
    assert packet.final_verdict == "PASS"
    assert packet.proceed is True


# ── invalid_contract kind specifics ───────────────────────────────────


def test_invalid_contract_kind_fail():
    packet = build_runtime_governance_sample_preflight_packet("invalid_contract")
    assert packet.final_verdict == "FAIL"
    assert packet.proceed is False
