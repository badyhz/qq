from __future__ import annotations

from pathlib import Path

import pytest

TASK_QUEUE_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd" / "runtime_governance_task_queue.md"
CURRENT_STATE_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "dev_prd" / "runtime_governance_current_state.md"


@pytest.fixture()
def task_queue_text() -> str:
    assert TASK_QUEUE_PATH.exists()
    return TASK_QUEUE_PATH.read_text(encoding="utf-8")


@pytest.fixture()
def current_state_text() -> str:
    assert CURRENT_STATE_PATH.exists()
    return CURRENT_STATE_PATH.read_text(encoding="utf-8")


class TestT1381T1400Compatibility:
    def test_task_queue_doc_exists(self) -> None:
        assert TASK_QUEUE_PATH.exists()

    def test_contains_t1361(self, task_queue_text: str) -> None:
        assert "T1361" in task_queue_text

    def test_current_state_doc_exists(self) -> None:
        assert CURRENT_STATE_PATH.exists()

    def test_release_hold_is_hold(self, current_state_text: str) -> None:
        assert "HOLD" in current_state_text

    def test_human_review_board_models_importable(self) -> None:
        from core.human_review_board_packet import HumanReviewBoardPacket
        from core.human_review_board_verdict import HumanReviewBoardVerdict
        assert HumanReviewBoardPacket is not None
        assert HumanReviewBoardVerdict is not None

    def test_implementation_boundary_importable(self) -> None:
        from core.implementation_boundary_contract import ImplementationBoundaryContract
        contract = ImplementationBoundaryContract(
            contract_id="test",
            allowed_scope=(),
            forbidden_paths=(),
            required_evidence=(),
            human_approval_required=True,
            release_hold="HOLD",
        )
        assert contract.release_hold == "HOLD"
