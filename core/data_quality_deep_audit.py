"""Data quality deep audit — OHLCV row validation.

Detects: impossible OHLC, zero volume, NaN, missing fields.
Pure functions. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class DataQualityFinding:
    """A single data quality finding."""
    severity: str  # HARD_BLOCK, WARNING, INFO
    reason_code: str
    affected_symbol: str
    affected_timeframe: str
    affected_split: str
    count: int
    block_promotion: bool
    details: str


@dataclass(frozen=True)
class DataQualityAuditResult:
    """Complete data quality audit result."""
    findings: Tuple[DataQualityFinding, ...]
    hard_blocks: Tuple[str, ...]
    warnings: Tuple[str, ...]
    total_rows_audited: int
    total_findings: int
    verdict: str  # PASS, PARTIAL, FAIL


def audit_ohlcv_rows(
    bars: Sequence[Dict[str, Any]],
    symbol: str = "",
    timeframe: str = "",
    split_id: str = "",
) -> Tuple[DataQualityFinding, ...]:
    """Audit OHLCV rows for data quality issues."""
    findings = []
    missing_count = 0
    zero_vol_count = 0
    impossible_ohlc_count = 0
    nan_count = 0

    for bar in bars:
        # Check required fields
        for field in ("open", "high", "low", "close", "volume"):
            if field not in bar or bar[field] is None:
                missing_count += 1
                continue
            val = bar[field]
            if isinstance(val, float) and val != val:  # NaN check
                nan_count += 1
                continue

        # Check impossible OHLC
        try:
            o, h, l, c = bar.get("open", 0), bar.get("high", 0), bar.get("low", 0), bar.get("close", 0)
            if h > 0 and l > 0:
                if l > h:
                    impossible_ohlc_count += 1
                elif o > h or o < l or c > h or c < l:
                    impossible_ohlc_count += 1
        except (TypeError, ValueError):
            impossible_ohlc_count += 1

        # Check zero volume
        vol = bar.get("volume", 0)
        if vol is not None and vol == 0:
            zero_vol_count += 1

    if missing_count > 0:
        findings.append(DataQualityFinding(
            severity="HARD_BLOCK", reason_code="MISSING_OHLCV_FIELDS",
            affected_symbol=symbol, affected_timeframe=timeframe,
            affected_split=split_id, count=missing_count,
            block_promotion=True,
            details=f"{missing_count} rows with missing OHLCV fields",
        ))

    if impossible_ohlc_count > 0:
        findings.append(DataQualityFinding(
            severity="HARD_BLOCK", reason_code="IMPOSSIBLE_OHLC",
            affected_symbol=symbol, affected_timeframe=timeframe,
            affected_split=split_id, count=impossible_ohlc_count,
            block_promotion=True,
            details=f"{impossible_ohlc_count} rows with impossible OHLC values",
        ))

    if nan_count > 0:
        findings.append(DataQualityFinding(
            severity="HARD_BLOCK", reason_code="NAN_METRICS",
            affected_symbol=symbol, affected_timeframe=timeframe,
            affected_split=split_id, count=nan_count,
            block_promotion=True,
            details=f"{nan_count} NaN values in OHLCV data",
        ))

    if zero_vol_count > 0:
        findings.append(DataQualityFinding(
            severity="WARNING", reason_code="ZERO_VOLUME",
            affected_symbol=symbol, affected_timeframe=timeframe,
            affected_split=split_id, count=zero_vol_count,
            block_promotion=False,
            details=f"{zero_vol_count} rows with zero volume",
        ))

    return tuple(findings)


def build_audit_result(
    findings: Tuple[DataQualityFinding, ...],
    total_rows: int = 0,
) -> DataQualityAuditResult:
    """Build audit result from findings."""
    hard_blocks = tuple(f.reason_code for f in findings if f.block_promotion)
    warnings = tuple(f.reason_code for f in findings if not f.block_promotion)

    if hard_blocks:
        verdict = "FAIL"
    elif warnings:
        verdict = "PARTIAL"
    else:
        verdict = "PASS"

    return DataQualityAuditResult(
        findings=findings,
        hard_blocks=hard_blocks,
        warnings=warnings,
        total_rows_audited=total_rows,
        total_findings=len(findings),
        verdict=verdict,
    )


def audit_result_to_dict(r: DataQualityAuditResult) -> Dict:
    return {
        "findings": [
            {
                "severity": f.severity, "reason_code": f.reason_code,
                "affected_symbol": f.affected_symbol, "affected_timeframe": f.affected_timeframe,
                "affected_split": f.affected_split, "count": f.count,
                "block_promotion": f.block_promotion, "details": f.details,
            }
            for f in r.findings
        ],
        "hard_blocks": list(r.hard_blocks),
        "warnings": list(r.warnings),
        "total_rows_audited": r.total_rows_audited,
        "total_findings": r.total_findings,
        "verdict": r.verdict,
    }
