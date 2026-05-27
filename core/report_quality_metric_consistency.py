"""Report quality metric consistency — check summary vs detail consistency.

No network.
"""
from __future__ import annotations

from typing import Any, Dict


def check_metric_consistency(
    summary: Dict[str, Any],
    detail: Dict[str, Any],
    tolerance: float = 0.001,
) -> Dict[str, Any]:
    """Check that summary metrics match detail metrics."""
    mismatches = []

    for key in summary:
        if key not in detail:
            continue
        s_val = summary[key]
        d_val = detail[key]
        if isinstance(s_val, (int, float)) and isinstance(d_val, (int, float)):
            if abs(s_val - d_val) > tolerance:
                mismatches.append({
                    "key": key,
                    "summary_value": s_val,
                    "detail_value": d_val,
                    "delta": abs(s_val - d_val),
                })

    return {
        "consistent": len(mismatches) == 0,
        "mismatches": mismatches,
        "warning": "" if not mismatches else f"METRIC_MISMATCH:{len(mismatches)}",
    }
