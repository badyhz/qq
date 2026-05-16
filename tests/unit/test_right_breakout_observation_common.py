from __future__ import annotations

from scripts.right_breakout_observation_common import (
    classify_observation_verdict,
    normalize_observation_config,
    render_observation_markdown,
    summarize_observation_results,
)


def test_normalize_observation_config() -> None:
    cfg = normalize_observation_config(
        symbols=[" btcusdt ", "ethusdt", ""],
        market_data_source="MOCK",
        timeframe="15m",
        limit=0,
        scan_cutoff_bars=0,
        horizons=[15, 5, -1, 15],
        min_score=60.0,
        volume_multiplier=1.2,
        lookback=1,
        walk_forward=False,
        min_history_bars=1,
        max_signals_per_symbol=0,
    )
    assert cfg["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert cfg["source"] == "mock"
    assert cfg["limit"] == 1
    assert cfg["scan_cutoff_bars"] == 1
    assert cfg["horizons"] == [5, 15]
    assert cfg["lookback"] == 5
    assert cfg["min_history_bars"] == 2
    assert cfg["max_signals_per_symbol"] == 1


def test_summary_counts_and_verdict() -> None:
    summary = summarize_observation_results(
        {
            "valid_count": 2,
            "rejected_count": 1,
            "warnings": ["x"],
            "candidate_outcomes": [{}, {}],
            "next_actions": ["continue_observation"],
        }
    )
    assert summary["valid_count"] == 2
    assert summary["rejected_count"] == 1
    assert summary["warnings_count"] == 1
    assert summary["outcomes_count"] == 2
    assert summary["verdict"] == "PARTIAL"


def test_classify_observation_verdict() -> None:
    assert classify_observation_verdict(valid_count=0, rejected_count=0, warnings_count=0) == "PARTIAL"
    assert classify_observation_verdict(valid_count=0, rejected_count=3, warnings_count=0) == "FAIL"
    assert classify_observation_verdict(valid_count=1, rejected_count=0, warnings_count=0) == "PASS"


def test_render_observation_markdown_sections() -> None:
    md = render_observation_markdown(
        {
            "verdict": "PASS",
            "valid_count": 3,
            "rejected_count": 1,
            "warnings_count": 0,
            "outcomes_count": 3,
            "next_actions": ["continue_observation", "inspect_params"],
        }
    )
    assert "# Right Breakout Observation" in md
    assert "## Summary" in md
    assert "## Next Actions" in md
    assert "- verdict: PASS" in md
    assert "- continue_observation" in md
