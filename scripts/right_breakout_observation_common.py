from __future__ import annotations

from typing import Any


def _parse_symbols(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in list(items or []):
        text = str(item or "").strip().upper()
        if text:
            out.append(text)
    return out


def _parse_horizons(items: list[int]) -> list[int]:
    out: set[int] = set()
    for item in list(items or []):
        try:
            value = int(item)
        except (TypeError, ValueError):
            continue
        if value > 0:
            out.add(value)
    return sorted(out) or [5, 15, 30]


def normalize_observation_config(
    *,
    symbols: list[str],
    market_data_source: str,
    timeframe: str,
    limit: int,
    scan_cutoff_bars: int,
    horizons: list[int] | None,
    min_score: float,
    volume_multiplier: float,
    lookback: int,
    walk_forward: bool,
    min_history_bars: int,
    max_signals_per_symbol: int,
) -> dict[str, Any]:
    return {
        "symbols": _parse_symbols(symbols),
        "source": str(market_data_source or "mock").strip().lower() or "mock",
        "timeframe": str(timeframe or "5m").strip() or "5m",
        "limit": max(1, int(limit)),
        "scan_cutoff_bars": max(1, int(scan_cutoff_bars)),
        "horizons": _parse_horizons(list(horizons or [5, 15, 30])),
        "min_score": float(min_score),
        "volume_multiplier": float(volume_multiplier),
        "lookback": max(5, int(lookback)),
        "walk_forward": bool(walk_forward),
        "min_history_bars": max(2, int(min_history_bars)),
        "max_signals_per_symbol": max(1, int(max_signals_per_symbol)),
    }


def classify_observation_verdict(
    *,
    valid_count: int,
    rejected_count: int,
    warnings_count: int,
) -> str:
    if valid_count <= 0 and rejected_count <= 0:
        return "PARTIAL"
    if valid_count <= 0 and rejected_count > 0:
        return "FAIL"
    if warnings_count > 0:
        return "PARTIAL"
    return "PASS"


def summarize_observation_results(payload: dict[str, Any]) -> dict[str, Any]:
    valid_count = int(payload.get("valid_count", 0) or 0)
    rejected_count = int(payload.get("rejected_count", 0) or 0)
    warnings = list(payload.get("warnings", []))
    outcomes = list(payload.get("candidate_outcomes", []))
    verdict = classify_observation_verdict(
        valid_count=valid_count,
        rejected_count=rejected_count,
        warnings_count=len(warnings),
    )
    return {
        "valid_count": valid_count,
        "rejected_count": rejected_count,
        "warnings_count": len(warnings),
        "outcomes_count": len(outcomes),
        "next_actions": list(payload.get("next_actions", [])),
        "verdict": verdict,
    }


def render_observation_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Right Breakout Observation",
        "",
        "## Summary",
        f"- verdict: {summary.get('verdict', '')}",
        f"- valid_count: {summary.get('valid_count', 0)}",
        f"- rejected_count: {summary.get('rejected_count', 0)}",
        f"- warnings_count: {summary.get('warnings_count', 0)}",
        f"- outcomes_count: {summary.get('outcomes_count', 0)}",
        "",
        "## Next Actions",
    ]
    actions = list(summary.get("next_actions", []))
    if not actions:
        lines.append("- none")
    else:
        for action in actions:
            lines.append(f"- {action}")
    return "\n".join(lines) + "\n"
