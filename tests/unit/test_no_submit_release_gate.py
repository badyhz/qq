from __future__ import annotations

import pytest

from core.no_submit_release_gate import NoSubmitReleaseGate
from core.no_submit_invariant import NoSubmitInvariant, INVARIANTS
from core.no_submit_denied_operation import NoSubmitDeniedOperation, DENIED_OPERATIONS


class TestNoSubmitReleaseGate:
    def test_create_gate_frozen(self) -> None:
        gate = NoSubmitReleaseGate(
            gate_id="G-001",
            invariants=("INV-001",),
            denied_operations=("place_order",),
            verdict="BLOCKED",
        )
        assert gate.gate_id == "G-001"
        with pytest.raises(AttributeError):
            gate.gate_id = "X"  # type: ignore[misc]

    def test_gate_verdict(self) -> None:
        gate = NoSubmitReleaseGate(
            gate_id="G-002",
            invariants=(),
            denied_operations=(),
            verdict="PASS",
        )
        assert gate.verdict == "PASS"

    def test_gate_multiple_invariants(self) -> None:
        gate = NoSubmitReleaseGate(
            gate_id="G-003",
            invariants=("INV-001", "INV-002", "INV-003"),
            denied_operations=(),
            verdict="FAIL",
        )
        assert len(gate.invariants) == 3


class TestNoSubmitInvariant:
    def test_invariants_tuple_populated(self) -> None:
        assert len(INVARIANTS) == 4

    def test_first_invariant_frozen(self) -> None:
        inv = INVARIANTS[0]
        assert inv.invariant_id == "INV-001"
        assert inv.description == "No order placement"
        with pytest.raises(AttributeError):
            inv.invariant_id = "X"  # type: ignore[misc]

    def test_all_have_check_function(self) -> None:
        for inv in INVARIANTS:
            assert inv.check_function_name.startswith("check_")


class TestNoSubmitDeniedOperation:
    def test_denied_ops_count(self) -> None:
        assert len(DENIED_OPERATIONS) == 6

    def test_first_denied_op_frozen(self) -> None:
        op = DENIED_OPERATIONS[0]
        assert op.operation == "place_order"
        assert op.severity == "critical"
        with pytest.raises(AttributeError):
            op.operation = "X"  # type: ignore[misc]

    def test_all_denied_ops_critical(self) -> None:
        for op in DENIED_OPERATIONS:
            assert op.severity == "critical"
