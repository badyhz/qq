"""T17501 — Shadow-to-Testnet Promotion Evidence Loader.

Pure deterministic. No I/O. No network.
Loads and validates all evidence required for shadow-to-testnet promotion decision.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

REQUIRED_EVIDENCE_TYPES: tuple[str, ...] = (
    "shadow_evidence_exists",
    "no_critical_blocker",
    "no_submit_guard_passed",
    "frozen_cleanup_finalized",
    "offline_regression_clean",
    "strategy_registry_exists",
    "testnet_dry_run_no_submit_default",
)

FORBIDDEN_PROMOTION_MODES: tuple[str, ...] = (
    "TESTNET_SUBMIT_ALLOWED",
    "REAL_SUBMIT_ALLOWED",
    "LIVE_TRADING_ALLOWED",
    "AUTO_SUBMIT_ENABLED",
)


@dataclass(frozen=True)
class PromotionEvidenceItem:
    """Single promotion evidence item."""
    evidence_id: str
    evidence_type: str
    status: str
    description: str
    source: str
    verified: bool
    blocking: bool

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "status": self.status,
            "description": self.description,
            "source": self.source,
            "verified": self.verified,
            "blocking": self.blocking,
        }


def build_evidence_item(
    evidence_type: str,
    status: str,
    description: str,
    source: str,
    verified: bool = False,
    blocking: bool = True,
) -> PromotionEvidenceItem:
    """Build a single promotion evidence item."""
    return PromotionEvidenceItem(
        evidence_id=f"promo_evidence_{evidence_type}",
        evidence_type=evidence_type,
        status=status,
        description=description,
        source=source,
        verified=verified,
        blocking=blocking,
    )


def load_evidence_from_cleanup(cleanup_report: dict) -> list[PromotionEvidenceItem]:
    """Load evidence from frozen cleanup governance."""
    items: list[PromotionEvidenceItem] = []

    cleanup_ready = cleanup_report.get("cleanup_ready_for_human_review", False)
    items.append(build_evidence_item(
        evidence_type="frozen_cleanup_finalized",
        status="PASS" if cleanup_ready else "FAIL",
        description=f"cleanup_ready_for_human_review={cleanup_ready}",
        source="frozen_cleanup_report",
        verified=cleanup_ready,
    ))

    return items


def load_evidence_from_shadow(shadow_data: dict) -> list[PromotionEvidenceItem]:
    """Load evidence from shadow experiment data."""
    items: list[PromotionEvidenceItem] = []

    shadow_exists = shadow_data.get("shadow_evidence_exists", False)
    items.append(build_evidence_item(
        evidence_type="shadow_evidence_exists",
        status="PASS" if shadow_exists else "FAIL",
        description=f"shadow_evidence_exists={shadow_exists}",
        source="shadow_experiment_data",
        verified=shadow_exists,
    ))

    stability = shadow_data.get("stability_score", 0.0)
    items.append(build_evidence_item(
        evidence_type="no_critical_blocker",
        status="PASS" if stability >= 0.5 else "FAIL",
        description=f"stability_score={stability}_threshold=0.5",
        source="shadow_stability_data",
        verified=stability >= 0.5,
    ))

    return items


def load_evidence_from_safety(safety_data: dict) -> list[PromotionEvidenceItem]:
    """Load evidence from no-submit safety checks."""
    items: list[PromotionEvidenceItem] = []

    guard_passed = safety_data.get("no_submit_guard_passed", False)
    items.append(build_evidence_item(
        evidence_type="no_submit_guard_passed",
        status="PASS" if guard_passed else "FAIL",
        description=f"no_submit_guard_passed={guard_passed}",
        source="execution_guard",
        verified=guard_passed,
    ))

    return items


def load_evidence_from_regression(regression_data: dict) -> list[PromotionEvidenceItem]:
    """Load evidence from offline regression tests."""
    items: list[PromotionEvidenceItem] = []

    clean = regression_data.get("offline_regression_clean", False)
    items.append(build_evidence_item(
        evidence_type="offline_regression_clean",
        status="PASS" if clean else "FAIL",
        description=f"offline_regression_clean={clean}",
        source="regression_pack",
        verified=clean,
    ))

    return items


def load_evidence_from_registry(registry_data: dict) -> list[PromotionEvidenceItem]:
    """Load evidence from strategy registry."""
    items: list[PromotionEvidenceItem] = []

    exists = registry_data.get("strategy_registry_exists", False)
    items.append(build_evidence_item(
        evidence_type="strategy_registry_exists",
        status="PASS" if exists else "FAIL",
        description=f"strategy_registry_exists={exists}",
        source="strategy_registry",
        verified=exists,
    ))

    return items


def load_testnet_default_evidence(testnet_data: dict) -> list[PromotionEvidenceItem]:
    """Load evidence for testnet dry-run no-submit default."""
    items: list[PromotionEvidenceItem] = []

    no_submit = testnet_data.get("testnet_dry_run_no_submit_default", True)
    items.append(build_evidence_item(
        evidence_type="testnet_dry_run_no_submit_default",
        status="PASS" if no_submit else "FAIL",
        description=f"testnet_dry_run_no_submit_default={no_submit}",
        source="testnet_config",
        verified=no_submit,
    ))

    return items


def load_all_promotion_evidence(
    cleanup_report: dict,
    shadow_data: dict,
    safety_data: dict,
    regression_data: dict,
    registry_data: dict,
    testnet_data: dict,
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[PromotionEvidenceItem]:
    """Load all promotion evidence from all sources."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    items: list[PromotionEvidenceItem] = []
    items.extend(load_evidence_from_cleanup(cleanup_report))
    items.extend(load_evidence_from_shadow(shadow_data))
    items.extend(load_evidence_from_safety(safety_data))
    items.extend(load_evidence_from_regression(regression_data))
    items.extend(load_evidence_from_registry(registry_data))
    items.extend(load_testnet_default_evidence(testnet_data))
    return items


def compute_evidence_hash(items: list[PromotionEvidenceItem]) -> str:
    raw = json.dumps([i.to_dict() for i in items], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
