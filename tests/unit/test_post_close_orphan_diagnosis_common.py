from __future__ import annotations

from scripts.post_close_orphan_diagnosis_common import (
    build_orphan_cleanup_recommendation,
    classify_post_close_orphan_state,
    render_post_close_orphan_markdown,
)


def test_classify_flat_clean() -> None:
    row = classify_post_close_orphan_state(
        {"symbol": "FETUSDT", "positionAmt": 0.0, "openAlgoOrdersCount": 0, "protection_status": "UNKNOWN"}
    )
    assert row["diagnosis"] == "FLAT_CLEAN"
    assert row["action_required"] == "none"


def test_classify_orphan_protection_with_command_recommendation() -> None:
    row = classify_post_close_orphan_state(
        {"symbol": "OPUSDT", "positionAmt": 0.0, "openAlgoOrdersCount": 2, "protection_status": "UNKNOWN"}
    )
    cmds = build_orphan_cleanup_recommendation(row)
    assert row["diagnosis"] == "ORPHAN_PROTECTION"
    assert len(cmds) == 2
    assert "--dry-run" in cmds[0]
    assert "--confirm" in cmds[1]


def test_classify_active_position_still_exists() -> None:
    row = classify_post_close_orphan_state(
        {"symbol": "BTCUSDT", "positionAmt": 1.0, "openAlgoOrdersCount": 0, "protection_status": "PARTIAL_PROTECTED"}
    )
    assert row["diagnosis"] == "PARTIAL_PROTECTED"
    assert "repair_missing_protection" in row["action_required"]


def test_render_markdown_sections() -> None:
    md = render_post_close_orphan_markdown(
        {
            "ts_utc": "2026-01-01T00:00:00Z",
            "env": "testnet",
            "symbols": ["FETUSDT"],
            "verdict": "PARTIAL",
            "verdict_reason": "orphan_protection_detected",
            "per_symbol_diagnosis": [
                {
                    "symbol": "FETUSDT",
                    "positionAmt": 0.0,
                    "openAlgoOrdersCount": 1,
                    "protection_status": "UNKNOWN",
                    "diagnosis": "ORPHAN_PROTECTION",
                    "action_required": "review_orphan_and_clean_if_confirmed",
                }
            ],
            "recommended_commands": ["echo test"],
        }
    )
    assert "# Post-Close Orphan Diagnosis" in md
    assert "## Recommended Commands" in md
    assert "`echo test`" in md
