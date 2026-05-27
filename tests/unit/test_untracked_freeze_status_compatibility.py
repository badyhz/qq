from __future__ import annotations

from pathlib import Path

import pytest

FREEZE_INVENTORY_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd" / "dirty_workspace_high_risk_freeze_inventory.md"


@pytest.fixture()
def inventory_text() -> str:
    assert FREEZE_INVENTORY_PATH.exists(), f"Freeze inventory doc not found: {FREEZE_INVENTORY_PATH}"
    return FREEZE_INVENTORY_PATH.read_text(encoding="utf-8")


class TestUntrackedFreezeStatusCompatibility:
    def test_doc_exists(self) -> None:
        assert FREEZE_INVENTORY_PATH.exists()

    def test_covers_9_high_risk_files(self, inventory_text: str) -> None:
        count = inventory_text.count("risk level: **HIGH**")
        assert count == 9, f"Expected 9 HIGH-risk files, found {count}"

    def test_release_hold_is_hold(self, inventory_text: str) -> None:
        assert "release_hold = **HOLD**" in inventory_text

    def test_frozen_status(self, inventory_text: str) -> None:
        assert "Status: FROZEN" in inventory_text
