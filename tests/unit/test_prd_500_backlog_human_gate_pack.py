"""T914 — tests for 500 backlog human gate pack.

Pure deterministic. No I/O. No timestamps. No random.
"""

import pytest

from core.prd_backlog_schema import PrdBacklog, PrdBacklogItem
from core.prd_500_backlog_human_gate_pack import (
    Prd500HumanGate,
    build_prd_500_human_gate_pack,
    human_gate_pack_to_dict,
    human_gate_pack_to_markdown,
)

# --- Fixture ---


def _make_backlog() -> PrdBacklog:
    return PrdBacklog(
        backlog_id="BL-TEST-001",
        items=[
            PrdBacklogItem(
                task_id="T-001",
                title="test task",
                milestone_id="M1",
                wave_id="W1",
                batch_id="B1",
                risk_level="LOW",
                status="pending",
                dependencies=[],
                allowed_file_patterns=[],
                forbidden_file_patterns=[],
                acceptance_command_ids=[],
                notes=[],
            ),
        ],
        total_expected_tasks=1,
        status="open",
        notes=[],
    )


# --- Tests ---


class TestHumanGatePack:
    def test_gates_present(self) -> None:
        gates = build_prd_500_human_gate_pack(_make_backlog())
        gate_ids = [g.gate_id for g in gates]
        assert "GATE-HIGH-RISK" in gate_ids
        assert "GATE-FROZEN" in gate_ids
        assert "GATE-RUNTIME-INTEGRATION" in gate_ids
        assert "GATE-HOOK-IMPLEMENTATION" in gate_ids
        assert "GATE-LIVE-EXECUTION" in gate_ids
        assert "GATE-PLANNER-AUTONOMOUS" in gate_ids

    def test_frozen_gate_required(self) -> None:
        gates = build_prd_500_human_gate_pack(_make_backlog())
        frozen = [g for g in gates if g.gate_id == "GATE-FROZEN"]
        assert len(frozen) == 1
        assert frozen[0].required is True

    def test_live_gate_required(self) -> None:
        gates = build_prd_500_human_gate_pack(_make_backlog())
        live = [g for g in gates if g.gate_id == "GATE-LIVE-EXECUTION"]
        assert len(live) == 1
        assert live[0].required is True

    def test_no_live_authorization(self) -> None:
        gates = build_prd_500_human_gate_pack(_make_backlog())
        live = [g for g in gates if g.gate_id == "GATE-LIVE-EXECUTION"]
        assert live[0].condition == "always blocked"

    def test_deterministic(self) -> None:
        b = _make_backlog()
        r1 = build_prd_500_human_gate_pack(b)
        r2 = build_prd_500_human_gate_pack(b)
        assert r1 == r2
        d1 = [human_gate_pack_to_dict(g) for g in r1]
        d2 = [human_gate_pack_to_dict(g) for g in r2]
        assert d1 == d2


class TestSerializers:
    def test_to_dict_keys(self) -> None:
        gates = build_prd_500_human_gate_pack(_make_backlog())
        for g in gates:
            d = human_gate_pack_to_dict(g)
            assert set(d.keys()) == {
                "gate_id",
                "applies_to",
                "required",
                "condition",
                "approval_options",
                "notes",
            }

    def test_to_markdown_contains_gate_id(self) -> None:
        gates = build_prd_500_human_gate_pack(_make_backlog())
        for g in gates:
            md = human_gate_pack_to_markdown(g)
            assert g.gate_id in md
