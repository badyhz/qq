from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskScriptKind:
    """T1212 - frozen enum-like class for medium-risk script kinds."""

    OPERATIONAL: str = "OPERATIONAL"
    VERIFICATION: str = "VERIFICATION"
    SHADOW: str = "SHADOW"
    TESTNET: str = "TESTNET"
    REMEDIATION: str = "REMEDIATION"

    _VALID: tuple[str, ...] = (
        "OPERATIONAL",
        "VERIFICATION",
        "SHADOW",
        "TESTNET",
        "REMEDIATION",
    )


def validate_kind(kind: str) -> str:
    """Validate that kind is a known MediumRiskScriptKind value."""
    valid = MediumRiskScriptKind._VALID
    if kind not in valid:
        raise ValueError(f"Invalid script kind: {kind!r}. Must be one of {valid}")
    return kind
