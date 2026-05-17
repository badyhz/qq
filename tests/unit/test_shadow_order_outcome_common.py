from __future__ import annotations

from scripts.shadow_order_outcome_common import (
    calculate_shadow_order_metrics,
    classify_shadow_order_outcome,
    render_shadow_order_outcome_markdown,
    summarize_shadow_order_outcomes,
)


def test_classify_shadow_order_outcome_cases() -> None:
    assert classify_shadow_order_outcome({"outcome_status": "fetch_failed"}) == "FAILED"
    assert classify_shadow_order_outcome({"order_level_exit_reason": "take_profit_triggered"}) == "TAKE_PROFIT"
    assert classify_shadow_order_outcome({"order_level_exit_reason": "stop_loss_triggered"}) == "STOP_LOSS"
    assert classify_shadow_order_outcome({"outcome_status": "ok", "order_level_exit_reason": "open"}) == "OPEN"


def test_summarize_and_metrics() -> None:
    rows = [
        {"outcome_status": "fetch_failed"},
        {"order_level_exit_reason": "take_profit_triggered"},
        {"order_level_exit_reason": "stop_loss_triggered"},
        {"outcome_status": "ok", "order_level_exit_reason": "open"},
    ]
    summary = summarize_shadow_order_outcomes(rows)
    metrics = calculate_shadow_order_metrics(rows)
    assert summary["failed_rows"] == 1
    assert summary["tp_rows"] == 1
    assert summary["sl_rows"] == 1
    assert summary["open_rows"] == 1
    assert metrics["total_rows"] == 4
    assert metrics["win_rate"] == 0.25


def test_render_markdown_sections() -> None:
    md = render_shadow_order_outcome_markdown(
        {
            "total_rows": 3,
            "failed_rows": 1,
            "tp_rows": 1,
            "sl_rows": 1,
            "open_rows": 0,
            "win_rate": 0.33333333,
            "counts": {"FAILED": 1, "TAKE_PROFIT": 1, "STOP_LOSS": 1},
        }
    )
    assert "# Shadow Order Outcome Summary" in md
    assert "## Counts" in md
    assert "- FAILED: 1" in md
