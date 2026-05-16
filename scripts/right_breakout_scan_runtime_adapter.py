from __future__ import annotations

from typing import Any


def _clean_symbols(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in list(items or []):
        text = str(item or "").strip().upper()
        if text:
            result.append(text)
    return result


def normalize_runtime_scan_config(
    *,
    symbols: list[str],
    timeframe: str,
    limit: int,
    max_candidates: int,
    min_score: float,
    volume_multiplier: float,
    lookback: int,
    market_data_source: str,
    dry_gate: bool,
    mock_gate: bool,
) -> dict[str, Any]:
    return {
        "symbols": _clean_symbols(symbols),
        "timeframe": str(timeframe or "5m").strip() or "5m",
        "limit": max(1, int(limit)),
        "max_candidates": max(0, int(max_candidates)),
        "min_score": float(min_score),
        "volume_multiplier": float(volume_multiplier),
        "lookback": max(5, int(lookback)),
        "market_data_source": str(market_data_source or "mock").strip().lower() or "mock",
        "dry_gate": bool(dry_gate),
        "mock_gate": bool(mock_gate),
    }


def classify_runtime_scan_status(
    *,
    valid_count: int,
    rejected_count: int,
    blocked_count: int,
    warnings_count: int,
) -> str:
    if valid_count <= 0 and blocked_count > 0:
        return "FAIL"
    if valid_count <= 0 and rejected_count <= 0:
        return "PARTIAL"
    if warnings_count > 0:
        return "PARTIAL"
    return "PASS"


def build_runtime_scan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    valid_count = int(payload.get("valid_count", 0) or 0)
    rejected_count = int(payload.get("rejected_count", 0) or 0)
    blocked_count = int(payload.get("gate_blocked", 0) or 0)
    warnings_count = len(list(payload.get("warnings", [])))
    verdict = classify_runtime_scan_status(
        valid_count=valid_count,
        rejected_count=rejected_count,
        blocked_count=blocked_count,
        warnings_count=warnings_count,
    )
    return {
        "valid_count": valid_count,
        "rejected_count": rejected_count,
        "blocked_count": blocked_count,
        "warnings_count": warnings_count,
        "symbols_count": int(payload.get("total_symbols", 0) or 0),
        "verdict": verdict,
    }


def render_runtime_scan_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Runtime Scan Summary",
        "",
        "## Counts",
        f"- verdict: {summary.get('verdict', '')}",
        f"- symbols_count: {summary.get('symbols_count', 0)}",
        f"- valid_count: {summary.get('valid_count', 0)}",
        f"- rejected_count: {summary.get('rejected_count', 0)}",
        f"- blocked_count: {summary.get('blocked_count', 0)}",
        f"- warnings_count: {summary.get('warnings_count', 0)}",
    ]
    return "\n".join(lines) + "\n"
