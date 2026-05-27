"""Runtime governance sample factory — pure sample object factory.

Deterministic. No I/O. No network. No random. No timestamps.
"""

from __future__ import annotations

from typing import Dict

from core.runtime_governance_contract import (
    RuntimeGovernanceInput,
    normalize_runtime_governance_input,
)
from core.runtime_governance_preflight_packet import (
    RuntimeGovernancePreflightPacket,
    build_runtime_governance_preflight_packet,
    preflight_packet_to_markdown,
)


# ── kind definitions ──────────────────────────────────────────────────

_SAMPLE_KINDS: Dict[str, dict] = {
    "pass": dict(
        run_id="sample-pass-001",
        adapter_id="sample-adapter",
        mode="shadow",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
    ),
    "fail": dict(
        run_id="",
        adapter_id="sample-adapter",
        mode="shadow",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
    ),
    "blocked": dict(
        run_id="sample-blocked-001",
        adapter_id="sample-adapter",
        mode="shadow",
        requested_action="submit",
        symbol="BTCUSDT",
        environment="prod",
        allow_network=False,
        allow_submit=True,
        allow_file_io=False,
    ),
    "warn_like": dict(
        run_id="sample-warn-001",
        adapter_id="sample-adapter",
        mode="dry_run",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
    ),
    "invalid_contract": dict(
        run_id="sample-invalid-001",
        adapter_id="sample-adapter",
        mode="unknown_mode",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
    ),
}


# ── builders ──────────────────────────────────────────────────────────


def build_runtime_governance_sample_input(kind: str) -> RuntimeGovernanceInput:
    """Build a sample RuntimeGovernanceInput for the given kind.

    Pure. Deterministic. Raises ValueError for unsupported kind.
    """
    if kind not in _SAMPLE_KINDS:
        raise ValueError(
            f"unsupported sample kind: {kind!r}; "
            f"expected one of: {', '.join(sorted(_SAMPLE_KINDS))}"
        )
    return normalize_runtime_governance_input(**_SAMPLE_KINDS[kind])


def build_runtime_governance_sample_preflight_packet(
    kind: str,
) -> RuntimeGovernancePreflightPacket:
    """Build a sample RuntimeGovernancePreflightPacket for the given kind.

    Pure. Deterministic. Raises ValueError for unsupported kind.
    """
    inp = build_runtime_governance_sample_input(kind)
    return build_runtime_governance_preflight_packet(inp)


def build_runtime_governance_sample_markdown(kind: str) -> str:
    """Build a deterministic markdown rendering for the given kind.

    Pure. Deterministic. Raises ValueError for unsupported kind.
    """
    packet = build_runtime_governance_sample_preflight_packet(kind)
    return preflight_packet_to_markdown(packet)
