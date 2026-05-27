from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanReviewGate:
    gate_id: str
    gate_type: str
    status: str
    required_evidence: tuple[str, ...]
    forbidden_approvals: tuple[str, ...]
    freeze_dependencies: tuple[str, ...]


def build_gate(
    gate_id: str,
    gate_type: str,
    status: str = "PENDING_APPROVAL",
    required_evidence: tuple[str, ...] = (),
    forbidden_approvals: tuple[str, ...] = (),
    freeze_dependencies: tuple[str, ...] = (),
) -> HumanReviewGate:
    return HumanReviewGate(
        gate_id=gate_id,
        gate_type=gate_type,
        status=status,
        required_evidence=tuple(required_evidence),
        forbidden_approvals=tuple(forbidden_approvals),
        freeze_dependencies=tuple(freeze_dependencies),
    )


def gate_to_dict(gate: HumanReviewGate) -> dict[str, object]:
    return {
        "gate_id": gate.gate_id,
        "gate_type": gate.gate_type,
        "status": gate.status,
        "required_evidence": list(gate.required_evidence),
        "forbidden_approvals": list(gate.forbidden_approvals),
        "freeze_dependencies": list(gate.freeze_dependencies),
    }
