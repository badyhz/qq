from __future__ import annotations

from scripts.right_breakout_param_observation_common import (
    build_param_grid_summary,
    classify_param_observation_verdict,
    normalize_param_scan_config,
    render_param_observation_markdown,
)


def test_normalize_param_scan_config() -> None:
    cfg = normalize_param_scan_config(
        symbols=[" btcusdt ", "ethusdt", ""],
        timeframes=["5m", "", "15m"],
        limit=0,
        max_candidates=-1,
        min_scores=[],
        volume_multipliers=[],
        lookbacks=[],
    )
    assert cfg["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert cfg["timeframes"] == ["5m", "15m"]
    assert cfg["limit"] == 1
    assert cfg["max_candidates"] == 0
    assert cfg["min_scores"] == [60.0]
    assert cfg["volume_multipliers"] == [1.2]
    assert cfg["lookbacks"] == [20]


def test_build_param_grid_summary() -> None:
    summary = build_param_grid_summary(
        {
            "total_param_sets": 12,
            "param_results": [{}, {}, {}],
            "warnings": ["x"],
        }
    )
    assert summary["total_param_sets"] == 12
    assert summary["results_count"] == 3
    assert summary["warnings_count"] == 1
    assert summary["verdict"] == "PARTIAL"


def test_classify_param_observation_verdict() -> None:
    assert classify_param_observation_verdict(total_param_sets=0, results_count=0, warnings_count=0) == "FAIL"
    assert classify_param_observation_verdict(total_param_sets=5, results_count=0, warnings_count=0) == "PARTIAL"
    assert classify_param_observation_verdict(total_param_sets=5, results_count=2, warnings_count=0) == "PASS"


def test_render_param_observation_markdown_sections() -> None:
    md = render_param_observation_markdown(
        {
            "verdict": "PASS",
            "total_param_sets": 10,
            "results_count": 8,
            "warnings_count": 0,
        }
    )
    assert "# Param Observation Summary" in md
    assert "## Counts" in md
    assert "- verdict: PASS" in md
    assert "- total_param_sets: 10" in md
