from __future__ import annotations

from typing import Any


def _clean_symbols(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in list(items or []):
        text = str(item or "").strip().upper()
        if text:
            out.append(text)
    return out


def _clean_timeframes(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in list(items or []):
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out or ["5m"]


def _clean_floats(items: list[float], fallback: list[float]) -> list[float]:
    out: list[float] = []
    for item in list(items or []):
        out.append(float(item))
    return out or list(fallback)


def _clean_ints(items: list[int], fallback: list[int]) -> list[int]:
    out: list[int] = []
    for item in list(items or []):
        out.append(int(item))
    return out or list(fallback)


def normalize_param_scan_config(
    *,
    symbols: list[str],
    timeframes: list[str],
    limit: int,
    max_candidates: int,
    min_scores: list[float],
    volume_multipliers: list[float],
    lookbacks: list[int],
) -> dict[str, Any]:
    return {
        "symbols": _clean_symbols(symbols),
        "timeframes": _clean_timeframes(timeframes),
        "limit": max(1, int(limit)),
        "max_candidates": max(0, int(max_candidates)),
        "min_scores": _clean_floats(min_scores, [60.0]),
        "volume_multipliers": _clean_floats(volume_multipliers, [1.2]),
        "lookbacks": _clean_ints(lookbacks, [20]),
    }


def classify_param_observation_verdict(
    *,
    total_param_sets: int,
    results_count: int,
    warnings_count: int,
) -> str:
    if total_param_sets <= 0:
        return "FAIL"
    if results_count <= 0:
        return "PARTIAL"
    if warnings_count > 0:
        return "PARTIAL"
    return "PASS"


def build_param_grid_summary(payload: dict[str, Any]) -> dict[str, Any]:
    total_param_sets = int(payload.get("total_param_sets", 0) or 0)
    results_count = len(list(payload.get("param_results", [])))
    warnings_count = len(list(payload.get("warnings", [])))
    verdict = classify_param_observation_verdict(
        total_param_sets=total_param_sets,
        results_count=results_count,
        warnings_count=warnings_count,
    )
    return {
        "total_param_sets": total_param_sets,
        "results_count": results_count,
        "warnings_count": warnings_count,
        "verdict": verdict,
    }


def render_param_observation_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Param Observation Summary",
        "",
        "## Counts",
        f"- verdict: {summary.get('verdict', '')}",
        f"- total_param_sets: {summary.get('total_param_sets', 0)}",
        f"- results_count: {summary.get('results_count', 0)}",
        f"- warnings_count: {summary.get('warnings_count', 0)}",
    ]
    return "\n".join(lines) + "\n"
