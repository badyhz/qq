from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.protection_monitor_report_common import (
    classify_protection_distance_state,
    summarize_protection_distance,
    classify_protection_trigger_outcome,
    summarize_protection_trigger_outcomes,
    render_protection_monitor_markdown,
)


def test_classify_protection_distance_state_healthy():
    row = {
        "protection_health": "HEALTHY",
        "severity": "INFO",
        "alerts": [],
    }
    assert classify_protection_distance_state(row) == "HEALTHY"


def test_classify_protection_distance_state_near_trigger():
    row = {
        "protection_health": "HEALTHY",
        "severity": "WARNING",
        "alerts": ["near_stop"],
    }
    assert classify_protection_distance_state(row) == "NEAR_TRIGGER"


def test_classify_protection_distance_state_invalid():
    row = {
        "protection_health": "MISSING_STOP_LOSS",
        "severity": "CRITICAL",
        "alerts": ["missing_stop_loss"],
    }
    assert classify_protection_distance_state(row) == "INVALID_PROTECTION"


def test_classify_protection_distance_state_no_position():
    row = {
        "protection_health": "NO_POSITION",
        "severity": "INFO",
        "alerts": ["no_position"],
    }
    assert classify_protection_distance_state(row) == "NO_POSITION"


def test_summarize_protection_distance():
    rows = [
        {
            "symbol": "FETUSDT",
            "protection_health": "HEALTHY",
            "severity": "INFO",
            "alerts": [],
        },
        {
            "symbol": "OPUSDT",
            "protection_health": "HEALTHY",
            "severity": "WARNING",
            "alerts": ["near_stop"],
        },
    ]
    summary = summarize_protection_distance(rows)
    assert summary["aggregate_status"] == "PARTIAL"
    assert summary["counts"]["HEALTHY"] == 1
    assert summary["counts"]["NEAR_TRIGGER"] == 1


def test_classify_protection_trigger_outcome_tp():
    row = {
        "outcome": "TAKE_PROFIT_TRIGGERED",
        "verdict": "PASS",
        "orphan_after_close": False,
    }
    assert classify_protection_trigger_outcome(row) == "TAKE_PROFIT_TRIGGERED"


def test_classify_protection_trigger_outcome_sl():
    row = {
        "outcome": "STOP_LOSS_TRIGGERED",
        "verdict": "PASS",
        "orphan_after_close": False,
    }
    assert classify_protection_trigger_outcome(row) == "STOP_LOSS_TRIGGERED"


def test_classify_protection_trigger_outcome_orphan():
    row = {
        "outcome": "STOP_LOSS_TRIGGERED",
        "verdict": "PASS",
        "orphan_after_close": True,
    }
    assert classify_protection_trigger_outcome(row) == "ORPHAN_AFTER_CLOSE"


def test_summarize_protection_trigger_outcomes():
    rows = [
        {
            "symbol": "OPUSDT",
            "outcome": "TAKE_PROFIT_TRIGGERED",
            "verdict": "PASS",
            "orphan_after_close": False,
        },
        {
            "symbol": "FETUSDT",
            "outcome": "STOP_LOSS_TRIGGERED",
            "verdict": "PASS",
            "orphan_after_close": True,
        },
    ]
    summary = summarize_protection_trigger_outcomes(rows)
    assert summary["aggregate_status"] == "PARTIAL"
    assert summary["counts"]["TAKE_PROFIT_TRIGGERED"] == 1
    assert summary["counts"]["ORPHAN_AFTER_CLOSE"] == 1


def test_render_protection_monitor_markdown():
    summary = {
        "aggregate_status": "PARTIAL",
        "counts": {"HEALTHY": 1, "NEAR_TRIGGER": 1},
        "per_symbol": [
            {
                "symbol": "FETUSDT",
                "side": "LONG",
                "markPrice": 100.0,
                "stop_loss_trigger_price": 95.0,
                "take_profit_trigger_price": 110.0,
                "distance_to_stop_pct": 5.0,
                "distance_to_take_profit_pct": 10.0,
                "protection_health": "HEALTHY",
                "severity": "INFO",
            }
        ],
    }
    md = render_protection_monitor_markdown(summary)
    assert "FETUSDT" in md
    assert "aggregate_status: PARTIAL" in md


def test_render_protection_monitor_markdown_outcome():
    summary = {
        "aggregate_status": "PARTIAL",
        "counts": {"TAKE_PROFIT_TRIGGERED": 1, "ORPHAN_AFTER_CLOSE": 1},
        "per_symbol": [
            {
                "symbol": "OPUSDT",
                "outcome": "TAKE_PROFIT_TRIGGERED",
                "verdict": "PASS",
                "orphan_after_close": False,
            }
        ],
    }
    md = render_protection_monitor_markdown(summary)
    assert "OPUSDT" in md
    assert "TAKE_PROFIT_TRIGGERED" in md


if __name__ == "__main__":
    import pytest
    pytest.main([str(Path(__file__)), "-v"])
