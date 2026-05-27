"""Research quality contract — safety constants and quality gate defaults.

Hard safety: release_hold=HOLD, advisory_only=True, human_review_required=True.
No network, no exchange, no runtime, no planner.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


# --- Safety constants (immutable) ---
RELEASE_HOLD_VALUE = "HOLD"
ADVISORY_ONLY = True
HUMAN_REVIEW_REQUIRED = True

SAFETY_FLAGS: Dict[str, bool] = {
    "no_live": True,
    "no_submit": True,
    "no_exchange": True,
    "no_runtime_integration": True,
    "no_planner_integration": True,
    "no_network": True,
}

FORBIDDEN_IMPORTS = (
    "binance", "ccxt", "exchange", "websocket",
    "requests", "httpx", "aiohttp",
    "runtime", "planner",
    "live_submit", "live_trading",
    "testnet_submit", "testnet_client",
)

QUALITY_GATE_VERSION = "v2.0.0"
QUALITY_GATE_GENERATED_BY = "research_quality_gate_v2"

REQUIRED_MANIFEST_FIELDS = (
    "release_hold", "no_live", "no_submit", "no_exchange",
    "no_runtime_integration", "no_planner_integration", "no_network",
    "advisory_only", "human_review_required",
    "deterministic_seed", "quality_gate_version", "strict_mode",
    "generated_by", "generated_at",
)


@dataclass(frozen=True)
class QualityContract:
    """Immutable quality gate contract."""
    release_hold: str = RELEASE_HOLD_VALUE
    advisory_only: bool = ADVISORY_ONLY
    human_review_required: bool = HUMAN_REVIEW_REQUIRED
    quality_gate_version: str = QUALITY_GATE_VERSION
    generated_by: str = QUALITY_GATE_GENERATED_BY

    def is_valid(self) -> bool:
        return (
            self.release_hold == RELEASE_HOLD_VALUE
            and self.advisory_only is True
            and self.human_review_required is True
        )

    def violations(self) -> Tuple[str, ...]:
        errs = []
        if self.release_hold != RELEASE_HOLD_VALUE:
            errs.append(f"release_hold={self.release_hold}, expected HOLD")
        if not self.advisory_only:
            errs.append("advisory_only must be True")
        if not self.human_review_required:
            errs.append("human_review_required must be True")
        return tuple(errs)

    def to_dict(self) -> Dict[str, object]:
        return {
            "release_hold": self.release_hold,
            "advisory_only": self.advisory_only,
            "human_review_required": self.human_review_required,
            "quality_gate_version": self.quality_gate_version,
            "generated_by": self.generated_by,
            "safety_flags": dict(SAFETY_FLAGS),
            "valid": self.is_valid(),
            "violations": list(self.violations()),
        }


DEFAULT_CONTRACT = QualityContract()


def assert_contract_valid(contract: QualityContract = DEFAULT_CONTRACT) -> None:
    """Raise ValueError if contract is invalid."""
    if not contract.is_valid():
        raise ValueError(f"Contract violations: {contract.violations()}")
