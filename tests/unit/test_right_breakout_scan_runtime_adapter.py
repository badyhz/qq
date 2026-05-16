from __future__ import annotations

from scripts.right_breakout_scan_runtime_adapter import (
    build_runtime_scan_summary,
    classify_runtime_scan_status,
    normalize_runtime_scan_config,
    render_runtime_scan_markdown,
)


def test_normalize_runtime_scan_config() -> None:
    cfg = normalize_runtime_scan_config(
        symbols=[" btcusdt ", "ethusdt", ""],
        timeframe="15m",
        limit=0,
        max_candidates=-1,
        min_score=60.0,
        volume_multiplier=1.2,
        lookback=2,
        market_data_source="MOCK",
        dry_gate=True,
        mock_gate=False,
    )
    assert cfg["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert cfg["timeframe"] == "15m"
    assert cfg["limit"] == 1
    assert cfg["max_candidates"] == 0
    assert cfg["lookback"] == 5
    assert cfg["market_data_source"] == "mock"
    assert cfg["dry_gate"] is True
    assert cfg["mock_gate"] is False


def test_build_runtime_scan_summary_and_verdict() -> None:
    summary = build_runtime_scan_summary(
        {
            "valid_count": 2,
            "rejected_count": 3,
            "gate_blocked": 1,
            "warnings": ["x", "y"],
            "total_symbols": 4,
        }
    )
    assert summary["valid_count"] == 2
    assert summary["rejected_count"] == 3
    assert summary["blocked_count"] == 1
    assert summary["warnings_count"] == 2
    assert summary["symbols_count"] == 4
    assert summary["verdict"] == "PARTIAL"


def test_classify_runtime_scan_status() -> None:
    assert classify_runtime_scan_status(valid_count=0, rejected_count=0, blocked_count=2, warnings_count=0) == "FAIL"
    assert classify_runtime_scan_status(valid_count=0, rejected_count=0, blocked_count=0, warnings_count=0) == "PARTIAL"
    assert classify_runtime_scan_status(valid_count=1, rejected_count=1, blocked_count=0, warnings_count=0) == "PASS"


def test_render_runtime_scan_markdown_sections() -> None:
    md = render_runtime_scan_markdown(
        {
            "verdict": "PASS",
            "symbols_count": 3,
            "valid_count": 2,
            "rejected_count": 1,
            "blocked_count": 0,
            "warnings_count": 0,
        }
    )
    assert "# Runtime Scan Summary" in md
    assert "## Counts" in md
    assert "- verdict: PASS" in md
    assert "- symbols_count: 3" in md
