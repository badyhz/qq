"""T1526 - Tests for FrozenBacklogInventory."""
from __future__ import annotations

import pytest

from core.frozen_backlog_inventory import FROZEN_BACKLOG_INVENTORY, FrozenBacklogInventory
from core.frozen_backlog_inventory_record import (
    VALID_CATEGORIES,
    VALID_RISK_CLASSES,
    FrozenBacklogInventoryRecord,
)


class TestFrozenBacklogInventoryConstant:
    """Tests for the module-level FROZEN_BACKLOG_INVENTORY constant."""

    def test_constant_exists(self) -> None:
        assert FROZEN_BACKLOG_INVENTORY is not None

    def test_constant_is_frozen_backlog_inventory(self) -> None:
        assert isinstance(FROZEN_BACKLOG_INVENTORY, FrozenBacklogInventory)

    def test_total_count_is_22(self) -> None:
        assert FROZEN_BACKLOG_INVENTORY.total_count == 22

    def test_high_risk_count_is_9(self) -> None:
        assert FROZEN_BACKLOG_INVENTORY.high_risk_count == 9

    def test_medium_risk_count_is_13(self) -> None:
        assert FROZEN_BACKLOG_INVENTORY.medium_risk_count == 13

    def test_records_length_matches_total(self) -> None:
        assert len(FROZEN_BACKLOG_INVENTORY.records) == 22

    def test_high_plus_medium_equals_total(self) -> None:
        inv = FROZEN_BACKLOG_INVENTORY
        assert inv.high_risk_count + inv.medium_risk_count == inv.total_count

    def test_all_records_have_release_hold(self) -> None:
        for rec in FROZEN_BACKLOG_INVENTORY.records:
            assert rec.release_hold == "HOLD", f"{rec.file_path} release_hold != HOLD"

    def test_no_duplicate_paths(self) -> None:
        paths = [r.file_path for r in FROZEN_BACKLOG_INVENTORY.records]
        assert len(paths) == len(set(paths)), "Duplicate file paths found"

    def test_all_categories_valid(self) -> None:
        for rec in FROZEN_BACKLOG_INVENTORY.records:
            assert rec.category in VALID_CATEGORIES, (
                f"{rec.file_path} has invalid category {rec.category!r}"
            )

    def test_all_risk_classes_valid(self) -> None:
        for rec in FROZEN_BACKLOG_INVENTORY.records:
            assert rec.risk_class in VALID_RISK_CLASSES, (
                f"{rec.file_path} has invalid risk_class {rec.risk_class!r}"
            )

    def test_high_risk_records_count(self) -> None:
        high = [r for r in FROZEN_BACKLOG_INVENTORY.records if r.risk_class == "HIGH"]
        assert len(high) == 9

    def test_medium_risk_records_count(self) -> None:
        medium = [r for r in FROZEN_BACKLOG_INVENTORY.records if r.risk_class == "MEDIUM"]
        assert len(medium) == 13

    def test_all_unlock_recommendations_valid(self) -> None:
        valid = ("HOLD", "PROMOTE", "DEFER", "REJECT")
        for rec in FROZEN_BACKLOG_INVENTORY.records:
            assert rec.unlock_recommendation in valid, (
                f"{rec.file_path} has invalid unlock_recommendation"
            )

    def test_inventory_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            FROZEN_BACKLOG_INVENTORY.total_count = 999  # type: ignore[misc]

    def test_records_are_frozen(self) -> None:
        rec = FROZEN_BACKLOG_INVENTORY.records[0]
        with pytest.raises(AttributeError):
            rec.release_hold = "RELEASE"  # type: ignore[misc]
