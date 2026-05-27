from __future__ import annotations

from pathlib import Path

CURRENT_STATE = Path("docs/dev_prd/runtime_governance_current_state.md")
CLOSEOUT_REPORT = Path("docs/dev_prd/read_only_hook_t961_t1060_closeout_report.md")
FREEZE_INVENTORY = Path("docs/dev_prd/dirty_workspace_high_risk_freeze_inventory.md")


def test_release_hold_in_current_state() -> None:
    text = CURRENT_STATE.read_text(encoding="utf-8")
    assert "Release hold: HOLD" in text or "release_hold" in text


def test_release_hold_in_closeout_report() -> None:
    text = CLOSEOUT_REPORT.read_text(encoding="utf-8")
    assert "Release hold: HOLD" in text or "release_hold" in text or "HOLD" in text


def test_release_hold_in_freeze_inventory() -> None:
    text = FREEZE_INVENTORY.read_text(encoding="utf-8")
    assert "HOLD" in text


def test_no_release_approved_anywhere() -> None:
    for doc in [CURRENT_STATE, CLOSEOUT_REPORT, FREEZE_INVENTORY]:
        text = doc.read_text(encoding="utf-8").lower()
        assert "release_hold = approved" not in text, f"Unexpected approved release in {doc}"
        assert "release_hold = released" not in text, f"Unexpected released in {doc}"
