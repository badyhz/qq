"""Data quality deep audit report — aggregate findings into report artifact.

Pure functions. No network.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from core.data_quality_deep_audit import DataQualityAuditResult, DataQualityFinding, audit_result_to_dict
from core.research_quality_contract import RELEASE_HOLD_VALUE


def build_data_quality_report(
    audit_result: DataQualityAuditResult,
    coverage_data: Dict = None,
    split_coverage_data: Dict = None,
    corruption_data: Tuple[Dict, ...] = (),
    seed: int = 424242,
    generated_at: str = None,
) -> Dict:
    """Build the data_quality_deep_audit.json artifact."""
    hard_blocks = list(audit_result.hard_blocks)
    warnings = list(audit_result.warnings)

    # Add corruption blocks
    for c in corruption_data:
        if c.get("block_promotion"):
            hard_blocks.append(f"CORRUPTION:{c.get('corruption_type', 'UNKNOWN')}")

    all_blocks = sorted(set(hard_blocks))
    all_warnings = sorted(set(warnings))

    verdict = "FAIL" if all_blocks else ("PARTIAL" if all_warnings else "PASS")

    return {
        "schema_version": "1.0.0",
        "generated_by": "data_quality_deep_audit",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": seed,
        "release_hold": RELEASE_HOLD_VALUE,
        "advisory_only": True,
        "human_review_required": True,
        "summary": {
            "total_rows_audited": audit_result.total_rows_audited,
            "total_findings": audit_result.total_findings,
            "hard_block_count": len(all_blocks),
            "warning_count": len(all_warnings),
        },
        "findings": [
            {
                "severity": f.severity, "reason_code": f.reason_code,
                "affected_symbol": f.affected_symbol, "affected_timeframe": f.affected_timeframe,
                "affected_split": f.affected_split, "count": f.count,
                "block_promotion": f.block_promotion, "details": f.details,
            }
            for f in audit_result.findings
        ],
        "hard_blocks": all_blocks,
        "warnings": all_warnings,
        "coverage": coverage_data or {},
        "split_coverage": split_coverage_data or {},
        "corruption": [c for c in corruption_data],
        "verdict": verdict,
    }
