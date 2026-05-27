"""Report quality check — completeness, required sections, warnings.

No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.research_quality_contract import RELEASE_HOLD_VALUE


REQUIRED_SECTIONS = [
    "summary", "data_quality", "split_leakage", "oos_validation",
    "parameter_robustness", "strategy_robustness", "portfolio_robustness",
    "negative_controls", "bootstrap", "regime", "promotion_gate",
]


def check_report_completeness(
    report: Dict[str, Any],
    required_sections: List[str] = None,
) -> Dict[str, Any]:
    """Check report for required sections."""
    if required_sections is None:
        required_sections = REQUIRED_SECTIONS

    present = []
    missing = []
    for section in required_sections:
        if section in report and report[section]:
            present.append(section)
        else:
            missing.append(section)

    complete = len(missing) == 0
    return {
        "complete": complete,
        "present_sections": present,
        "missing_sections": missing,
        "warning": "" if complete else f"MISSING_SECTIONS:{','.join(missing)}",
    }


def check_empty_nan_metrics(
    report: Dict[str, Any],
    critical_keys: List[str] = None,
) -> Dict[str, Any]:
    """Check for empty or NaN critical metrics."""
    if critical_keys is None:
        critical_keys = ["composite_score", "stability_score", "verdict"]

    issues = []
    for key in critical_keys:
        val = report.get(key)
        if val is None:
            issues.append(f"NULL:{key}")
        elif isinstance(val, float) and val != val:
            issues.append(f"NAN:{key}")
        elif isinstance(val, str) and not val:
            issues.append(f"EMPTY:{key}")

    return {
        "clean": len(issues) == 0,
        "issues": issues,
        "warning": "" if not issues else f"METRIC_ISSUES:{','.join(issues)}",
    }


def build_report_quality_check(
    report: Dict[str, Any],
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build report_quality_check.json."""
    completeness = check_report_completeness(report)
    metric_check = check_empty_nan_metrics(report)

    warnings = []
    blocks = []

    if not completeness["complete"]:
        warnings.append(completeness["warning"])
    if not metric_check["clean"]:
        blocks.append("METRIC_INCONSISTENCY")

    return {
        "schema_version": "1.0.0",
        "generated_by": "report_quality_check",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "completeness": completeness,
        "metric_check": metric_check,
        "warnings": warnings,
        "hard_blocks": blocks,
        "verdict": "FAIL" if blocks else ("PARTIAL" if warnings else "PASS"),
    }
