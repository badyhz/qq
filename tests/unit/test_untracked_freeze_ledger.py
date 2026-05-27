from __future__ import annotations

import pytest

from core.untracked_freeze_ledger import UntrackedFreezeLedger
from core.untracked_file_state import UntrackedFileState
from core.untracked_risk_class import UntrackedRiskClass


class TestUntrackedFreezeLedger:
    def test_create_ledger_frozen(self) -> None:
        ledger = UntrackedFreezeLedger(
            ledger_id="L-001",
            entries=(),
            frozen_files=(),
            release_hold=False,
        )
        assert ledger.ledger_id == "L-001"
        with pytest.raises(AttributeError):
            ledger.ledger_id = "X"  # type: ignore[misc]

    def test_is_empty(self) -> None:
        ledger = UntrackedFreezeLedger(
            ledger_id="L-002",
            entries=(),
            frozen_files=(),
            release_hold=False,
        )
        assert ledger.is_empty() is True

    def test_frozen_count(self) -> None:
        ledger = UntrackedFreezeLedger(
            ledger_id="L-003",
            entries=(),
            frozen_files=("a.py", "b.py", "c.py"),
            release_hold=True,
        )
        assert ledger.frozen_count() == 3

    def test_has_release_hold(self) -> None:
        ledger = UntrackedFreezeLedger(
            ledger_id="L-004",
            entries=(),
            frozen_files=(),
            release_hold=True,
        )
        assert ledger.has_release_hold() is True

    def test_ledger_to_dict(self) -> None:
        ledger = UntrackedFreezeLedger(
            ledger_id="L-005",
            entries=(),
            frozen_files=("x.py",),
            release_hold=False,
        )
        d = ledger.ledger_to_dict()
        assert d["ledger_id"] == "L-005"
        assert d["release_hold"] is False


class TestUntrackedFileState:
    def test_valid_states(self) -> None:
        for val in ("NEW", "STALE", "FROZEN", "DUPLICATE", "ORPHAN", "QUARANTINED"):
            s = UntrackedFileState(val)
            assert s.value == val

    def test_invalid_state_raises(self) -> None:
        with pytest.raises(ValueError):
            UntrackedFileState("INVALID")

    def test_equality(self) -> None:
        a = UntrackedFileState("FROZEN")
        b = UntrackedFileState("FROZEN")
        assert a == b
        assert a == "FROZEN"


class TestUntrackedRiskClass:
    def test_valid_classes(self) -> None:
        for val in ("HIGH", "MEDIUM", "LOW"):
            r = UntrackedRiskClass(val)
            assert r.value == val

    def test_invalid_class_raises(self) -> None:
        with pytest.raises(ValueError):
            UntrackedRiskClass("EXTREME")

    def test_equality(self) -> None:
        a = UntrackedRiskClass("HIGH")
        b = UntrackedRiskClass("HIGH")
        assert a == b
        assert a == "HIGH"
