#!/usr/bin/env python3
"""CLI renderer for governance failure regression packets.

Deterministic. No file I/O. No network. Stdout only.

Usage:
    python scripts/render_governance_failure_regression_packet.py --sample pass
    python scripts/render_governance_failure_regression_packet.py --sample fail --format json
    python scripts/render_governance_failure_regression_packet.py --sample blocked --strict
"""

from __future__ import annotations

import argparse
import json
import sys

from core.governance_failure_taxonomy import (
    FailureCategory,
    FailureSeverity,
    GovernanceFailure,
)
from core.governance_failure_regression_packet import (
    build_governance_failure_regression_packet,
    packet_to_dict,
    packet_to_markdown,
)

# ── sample data builders ──────────────────────────────────────────────


def _build_pass_failures() -> list[GovernanceFailure]:
    """No failures → PASS verdict."""
    return []


def _build_warn_failures() -> list[GovernanceFailure]:
    """Low-severity failures → WARN verdict."""
    return [
        GovernanceFailure(
            category=FailureCategory.RATE_LIMIT,
            severity=FailureSeverity.WARNING,
            code="RATE_LIMIT_429",
            message="Rate limited by upstream",
            source="binance_rest",
            retryable=True,
            metadata={"endpoint": "/api/v3/order"},
        ),
    ]


def _build_fail_failures() -> list[GovernanceFailure]:
    """Error-severity failures → FAIL verdict."""
    return [
        GovernanceFailure(
            category=FailureCategory.ADAPTER_FAILURE,
            severity=FailureSeverity.ERROR,
            code="ADAPTER_FAILURE",
            message="Adapter returned unexpected schema",
            source="binance_ws",
            retryable=False,
            metadata={"field": "orderId"},
        ),
        GovernanceFailure(
            category=FailureCategory.RATE_LIMIT,
            severity=FailureSeverity.WARNING,
            code="RATE_LIMIT_429",
            message="Rate limited by upstream",
            source="binance_rest",
            retryable=True,
            metadata={},
        ),
    ]


def _build_blocked_failures() -> list[GovernanceFailure]:
    """Critical non-retryable failure → BLOCKED verdict."""
    return [
        GovernanceFailure(
            category=FailureCategory.POLICY_BLOCK,
            severity=FailureSeverity.CRITICAL,
            code="POLICY_BLOCK",
            message="Policy forbids live trading in dry-run mode",
            source="risk_manager",
            retryable=False,
            metadata={"mode": "dry-run", "action": "submit_order"},
        ),
        GovernanceFailure(
            category=FailureCategory.ADAPTER_FAILURE,
            severity=FailureSeverity.ERROR,
            code="ADAPTER_FAILURE",
            message="Adapter returned unexpected schema",
            source="binance_ws",
            retryable=False,
            metadata={"field": "orderId"},
        ),
    ]


_SAMPLE_BUILDERS = {
    "pass": _build_pass_failures,
    "warn": _build_warn_failures,
    "fail": _build_fail_failures,
    "blocked": _build_blocked_failures,
}

# ── renderers ─────────────────────────────────────────────────────────


def render_markdown(sample: str) -> str:
    """Render sample as deterministic markdown."""
    failures = _SAMPLE_BUILDERS[sample]()
    packet = build_governance_failure_regression_packet(
        failures,
        title=f"Governance Failure Regression — {sample.upper()}",
    )
    return packet_to_markdown(packet)


def render_json(sample: str) -> str:
    """Render sample as deterministic JSON with stable key ordering."""
    failures = _SAMPLE_BUILDERS[sample]()
    packet = build_governance_failure_regression_packet(
        failures,
        title=f"Governance Failure Regression — {sample.upper()}",
    )
    return json.dumps(packet_to_dict(packet), indent=2, sort_keys=True)


_RENDERERS = {
    "markdown": render_markdown,
    "json": render_json,
}

# ── CLI ───────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render governance failure regression packets to stdout.",
    )
    parser.add_argument(
        "--sample",
        required=True,
        choices=sorted(_SAMPLE_BUILDERS.keys()),
        help="Sample scenario to render.",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        default="markdown",
        choices=sorted(_RENDERERS.keys()),
        help="Output format (default: markdown).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 for FAIL/BLOCKED samples.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    renderer = _RENDERERS[args.fmt]
    output = renderer(args.sample)
    print(output)

    if args.strict and args.sample in ("fail", "blocked"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
