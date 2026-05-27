from __future__ import annotations

import pytest

from core.implementation_boundary_contract import ImplementationBoundaryContract


class TestImplementationBoundaryContract:
    def test_create_contract(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-001",
            allowed_scope=("core/*.py", "docs/dev_prd/*.md"),
            forbidden_paths=("core/live_runner.py", "scripts/submit_*.py"),
            required_evidence=("dry_run_proof", "human_approval"),
            human_approval_required=True,
            release_hold="HOLD",
        )
        assert contract.contract_id == "IBC-001"

    def test_immutable(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-002",
            allowed_scope=(),
            forbidden_paths=(),
            required_evidence=(),
            human_approval_required=True,
            release_hold="HOLD",
        )
        with pytest.raises(AttributeError):
            contract.contract_id = "X"  # type: ignore[misc]

    def test_release_hold_must_be_hold(self) -> None:
        with pytest.raises(ValueError, match="HOLD"):
            ImplementationBoundaryContract(
                contract_id="IBC-003",
                allowed_scope=(),
                forbidden_paths=(),
                required_evidence=(),
                human_approval_required=True,
                release_hold="RELEASE",
            )

    def test_is_path_forbidden(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-004",
            allowed_scope=("core/*.py",),
            forbidden_paths=("core/live_runner.py", "scripts/submit_*.py"),
            required_evidence=(),
            human_approval_required=True,
            release_hold="HOLD",
        )
        assert contract.is_path_forbidden("core/live_runner.py") is True
        assert contract.is_path_forbidden("core/safe_module.py") is False

    def test_is_in_scope(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-005",
            allowed_scope=("core/*.py", "docs/dev_prd/*.md"),
            forbidden_paths=(),
            required_evidence=(),
            human_approval_required=False,
            release_hold="HOLD",
        )
        assert contract.is_in_scope("core/*.py") is True
        assert contract.is_in_scope("scripts/run_*.py") is False

    def test_human_approval_required(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-006",
            allowed_scope=(),
            forbidden_paths=(),
            required_evidence=("dry_run_proof",),
            human_approval_required=True,
            release_hold="HOLD",
        )
        assert contract.human_approval_required is True

    def test_required_evidence_tuple(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-007",
            allowed_scope=(),
            forbidden_paths=(),
            required_evidence=("dry_run_proof", "human_approval", "rollback_plan"),
            human_approval_required=True,
            release_hold="HOLD",
        )
        assert len(contract.required_evidence) == 3

    def test_empty_scope(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-008",
            allowed_scope=(),
            forbidden_paths=(),
            required_evidence=(),
            human_approval_required=False,
            release_hold="HOLD",
        )
        assert contract.is_in_scope("anything") is False

    def test_empty_forbidden(self) -> None:
        contract = ImplementationBoundaryContract(
            contract_id="IBC-009",
            allowed_scope=(),
            forbidden_paths=(),
            required_evidence=(),
            human_approval_required=False,
            release_hold="HOLD",
        )
        assert contract.is_path_forbidden("anything") is False
