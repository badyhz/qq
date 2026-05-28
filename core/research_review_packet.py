"""Research review packet — build deterministic offline human review packet.

Program A: Review Packet Builder.
Builds review_packet.json from quality gate, artifact browser, comparison analytics.

No network. No exchange. No runtime. No planner.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.research_quality_contract import (
    ADVISORY_ONLY,
    HUMAN_REVIEW_REQUIRED,
    RELEASE_HOLD_VALUE,
    SAFETY_FLAGS,
)

REVIEW_PACKET_VERSION = "1.0.0"
REVIEW_PACKET_GENERATED_BY = "research_human_review"

ALLOWED_RECOMMENDED_DECISIONS = (
    "BLOCKED",
    "NEEDS_MORE_RESEARCH",
    "REVIEW_ACCEPTED_ADVISORY_ONLY",
)

FORBIDDEN_DECISIONS = (
    "APPROVE_LIVE",
    "APPROVE_TESTNET_SUBMIT",
    "APPROVE_RUNTIME",
    "AUTO_PROMOTE",
)

PROMOTION_BLOCK_STATEMENT = (
    "This review packet is advisory only. No decision in this packet authorizes "
    "live trading, testnet submission, runtime integration, planner integration, "
    "or any form of auto-promotion. release_hold remains HOLD."
)


def compute_source_hashes(source_dirs: Dict[str, Path]) -> Dict[str, str]:
    """Compute SHA256 hashes of source directory contents."""
    hashes: Dict[str, str] = {}
    for label, d in sorted(source_dirs.items()):
        if not d.exists():
            continue
        all_files = sorted(f for f in d.iterdir() if f.is_file())
        combined = b""
        for f in all_files:
            combined += f.read_bytes()
        hashes[label] = hashlib.sha256(combined).hexdigest()
    return hashes


def extract_verdict_from_dir(source_dir: Path, manifest_name: str = "manifest.json") -> str:
    """Extract verdict from a source directory's manifest."""
    manifest_path = source_dir / manifest_name
    if not manifest_path.exists():
        return "MISSING"
    try:
        data = json.loads(manifest_path.read_text())
        # Check for safety validity
        if data.get("release_hold") != RELEASE_HOLD_VALUE:
            return "INVALID_SAFETY"
        if not data.get("advisory_only", False):
            return "INVALID_SAFETY"
        return "PASS"
    except (json.JSONDecodeError, ValueError):
        return "CORRUPTED"


def extract_blockers_from_quality(quality_dir: Path) -> List[Dict[str, Any]]:
    """Extract blockers from quality gate output."""
    blockers: List[Dict[str, Any]] = []
    summary_path = quality_dir / "quality_gate_summary.json"
    if not summary_path.exists():
        blockers.append({
            "blocker_id": "QUALITY_SUMMARY_MISSING",
            "source": "quality_gate",
            "severity": "CRITICAL",
            "description": "quality_gate_summary.json not found",
        })
        return blockers

    try:
        summary = json.loads(summary_path.read_text())
        overall = summary.get("overall_verdict", "UNKNOWN")
        if overall == "FAIL":
            blockers.append({
                "blocker_id": "QUALITY_GATE_FAIL",
                "source": "quality_gate",
                "severity": "CRITICAL",
                "description": "Quality gate overall verdict is FAIL",
            })
        elif overall == "PARTIAL":
            blockers.append({
                "blocker_id": "QUALITY_GATE_PARTIAL",
                "source": "quality_gate",
                "severity": "WARNING",
                "description": "Quality gate overall verdict is PARTIAL",
            })
    except (json.JSONDecodeError, ValueError):
        blockers.append({
            "blocker_id": "QUALITY_SUMMARY_CORRUPTED",
            "source": "quality_gate",
            "severity": "CRITICAL",
            "description": "quality_gate_summary.json is corrupted",
        })

    return blockers


def extract_blockers_from_comparison(comparison_dir: Path) -> List[Dict[str, Any]]:
    """Extract blockers from comparison analytics output."""
    blockers: List[Dict[str, Any]] = []
    regression_path = comparison_dir / "regression_report.json"
    if not regression_path.exists():
        blockers.append({
            "blocker_id": "COMPARISON_REGRESSION_MISSING",
            "source": "comparison_analytics",
            "severity": "WARNING",
            "description": "regression_report.json not found",
        })
        return blockers

    try:
        regression = json.loads(regression_path.read_text())
        if regression.get("has_any_safety_regression", False):
            blockers.append({
                "blocker_id": "COMPARISON_SAFETY_REGRESSION",
                "source": "comparison_analytics",
                "severity": "CRITICAL",
                "description": "Safety regression detected in comparison",
            })
    except (json.JSONDecodeError, ValueError):
        blockers.append({
            "blocker_id": "COMPARISON_REGRESSION_CORRUPTED",
            "source": "comparison_analytics",
            "severity": "CRITICAL",
            "description": "regression_report.json is corrupted",
        })

    return blockers


def determine_recommended_decision(
    blockers: List[Dict[str, Any]],
) -> str:
    """Determine recommended decision based on blockers."""
    critical = [b for b in blockers if b.get("severity") == "CRITICAL"]
    if critical:
        return "BLOCKED"
    warnings = [b for b in blockers if b.get("severity") == "WARNING"]
    if warnings:
        return "NEEDS_MORE_RESEARCH"
    return "REVIEW_ACCEPTED_ADVISORY_ONLY"


def build_evidence_links(
    quality_dir: Path,
    browser_dir: Path,
    comparison_dir: Path,
) -> List[Dict[str, str]]:
    """Build evidence links from source directories."""
    links: List[Dict[str, str]] = []
    for label, d in [("quality_gate", quality_dir), ("artifact_browser", browser_dir),
                     ("comparison_analytics", comparison_dir)]:
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix in (".json", ".md", ".html"):
                    links.append({
                        "source": label,
                        "filename": f.name,
                        "path": str(f),
                    })
    return links


REQUIRED_REVIEW_SECTIONS = (
    "safety_flags",
    "release_hold",
    "advisory_only",
    "human_review_required",
    "quality_gate_review",
    "artifact_browser_review",
    "comparison_analytics_review",
    "blockers_review",
    "warnings_review",
    "negative_controls_review",
    "bootstrap_uncertainty_review",
    "regime_risk_review",
    "portfolio_overlap_review",
    "reproducibility_review",
    "artifact_hashes_review",
    "no_runtime_testnet_live_escalation",
    "final_manual_decision",
)


def build_review_packet(
    quality_dir: Path,
    browser_dir: Path,
    comparison_dir: Path,
    source_hashes: Dict[str, str],
    generated_at: str = "deterministic",
    strict_mode: bool = True,
) -> Dict[str, Any]:
    """Build complete review packet."""
    quality_verdict = extract_verdict_from_dir(quality_dir)
    browser_verdict = extract_verdict_from_dir(browser_dir)
    comparison_verdict = extract_verdict_from_dir(comparison_dir)

    blockers: List[Dict[str, Any]] = []
    blockers.extend(extract_blockers_from_quality(quality_dir))
    blockers.extend(extract_blockers_from_comparison(comparison_dir))

    warnings = [b for b in blockers if b.get("severity") == "WARNING"]
    critical_blockers = [b for b in blockers if b.get("severity") == "CRITICAL"]

    recommended = determine_recommended_decision(blockers)

    evidence_links = build_evidence_links(quality_dir, browser_dir, comparison_dir)

    packet: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "packet_id": f"review_packet_{generated_at}",
        "generated_at": generated_at,
        "generated_by": REVIEW_PACKET_GENERATED_BY,
        "source_dirs": {
            "quality_gate": str(quality_dir),
            "artifact_browser": str(browser_dir),
            "comparison_analytics": str(comparison_dir),
        },
        "source_hashes": source_hashes,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": ADVISORY_ONLY,
        "human_review_required": HUMAN_REVIEW_REQUIRED,
        "no_live": SAFETY_FLAGS["no_live"],
        "no_submit": SAFETY_FLAGS["no_submit"],
        "no_exchange": SAFETY_FLAGS["no_exchange"],
        "no_network": SAFETY_FLAGS["no_network"],
        "no_runtime_integration": SAFETY_FLAGS["no_runtime_integration"],
        "no_planner_integration": SAFETY_FLAGS["no_planner_integration"],
        "quality_verdict": quality_verdict,
        "browser_verdict": browser_verdict,
        "comparison_verdict": comparison_verdict,
        "blockers": blockers,
        "warnings": [w.get("description", "") for w in warnings],
        "evidence_links": evidence_links,
        "required_review_sections": list(REQUIRED_REVIEW_SECTIONS),
        "recommended_decision": recommended,
        "allowed_decisions": list(ALLOWED_RECOMMENDED_DECISIONS),
        "forbidden_decisions": list(FORBIDDEN_DECISIONS),
        "promotion_block_statement": PROMOTION_BLOCK_STATEMENT,
    }

    return packet


def validate_review_packet_safety(packet: Dict[str, Any]) -> Tuple[bool, Tuple[str, ...]]:
    """Validate review packet safety flags. Returns (valid, errors)."""
    errors: List[str] = []

    if packet.get("release_hold") != RELEASE_HOLD_VALUE:
        errors.append(f"release_hold={packet.get('release_hold')!r}, expected HOLD")
    if not packet.get("advisory_only", False):
        errors.append("advisory_only must be True")
    if not packet.get("human_review_required", False):
        errors.append("human_review_required must be True")
    if not packet.get("no_network", False):
        errors.append("no_network must be True")
    if not packet.get("no_live", False):
        errors.append("no_live must be True")

    # Check forbidden decisions are NOT in allowed list
    allowed = set(packet.get("allowed_decisions", []))
    for fd in FORBIDDEN_DECISIONS:
        if fd in allowed:
            errors.append(f"forbidden decision {fd} found in allowed_decisions")

    # Check recommended decision is valid
    rec = packet.get("recommended_decision", "")
    if rec not in ALLOWED_RECOMMENDED_DECISIONS:
        errors.append(f"recommended_decision={rec!r} not in allowed list")

    return (len(errors) == 0, tuple(errors))
