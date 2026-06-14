"""Operator review index."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ReviewArtifact:
    artifact_id: str
    category: str
    title: str
    path: str
    status: str  # AVAILABLE, STUB_ONLY, NOT_IMPLEMENTED
    def to_dict(self) -> dict:
        return {"artifact_id": self.artifact_id, "category": self.category, "title": self.title, "path": self.path, "status": self.status}


@dataclass(frozen=True)
class OperatorReviewIndex:
    index_id: str
    created_at: str
    artifacts: tuple[ReviewArtifact, ...]
    def to_dict(self) -> dict:
        return {"index_id": self.index_id, "created_at": self.created_at, "artifacts": [a.to_dict() for a in self.artifacts]}


ARTIFACTS = (
    ReviewArtifact("ART_001", "replay", "Replay Traces", "data/runtime/testnet_mock_replay/replay_traces.json", "AVAILABLE"),
    ReviewArtifact("ART_002", "replay", "Scenario Matrix", "data/runtime/testnet_mock_replay/replay_scenario_matrix.json", "AVAILABLE"),
    ReviewArtifact("ART_003", "evidence", "Evidence Bundle", "data/runtime/testnet_mock_replay/evidence_bundle.json", "AVAILABLE"),
    ReviewArtifact("ART_004", "approval", "Approval Packet v3", "data/runtime/testnet_mock_replay/human_approval_packet_v3.json", "AVAILABLE"),
    ReviewArtifact("ART_005", "governance", "Trace Validator Checks", "data/runtime/testnet_mock_replay/trace_validator_checks.json", "AVAILABLE"),
    ReviewArtifact("ART_006", "safety", "Safety Regression Report", "data/runtime/testnet_mock_replay/replay_safety_regression.json", "AVAILABLE"),
    ReviewArtifact("ART_007", "transport", "Mock Transport Contract", "data/runtime/testnet_mock_transport/mock_transport_contract.json", "AVAILABLE"),
    ReviewArtifact("ART_008", "transport", "Vault Stub State", "data/runtime/testnet_mock_transport/vault_stub_state.json", "AVAILABLE"),
    ReviewArtifact("ART_009", "transport", "Adapter Skeleton Report", "data/runtime/testnet_mock_transport/adapter_skeleton_report.md", "AVAILABLE"),
    ReviewArtifact("ART_010", "governance", "Field-Test Governance Pack", "data/runtime/testnet_mock_transport/field_test_governance_pack.json", "AVAILABLE"),
    ReviewArtifact("ART_011", "spec", "External Adapter Spec", "data/runtime/testnet_adapter_spec/external_adapter_spec.md", "AVAILABLE"),
    ReviewArtifact("ART_012", "spec", "Credential Vault Architecture", "data/runtime/testnet_adapter_spec/credential_vault_architecture.md", "AVAILABLE"),
    ReviewArtifact("ART_013", "approval", "Approval Packet Comparator", "data/runtime/testnet_mock_review/approval_packet_comparison.json", "STUB_ONLY"),
    ReviewArtifact("ART_014", "review", "Evidence Browser Result", "data/runtime/testnet_mock_review/evidence_browser_result.json", "STUB_ONLY"),
    ReviewArtifact("ART_015", "review", "Review Navigation Report", "data/runtime/testnet_mock_review/review_navigation_report.json", "STUB_ONLY"),
)


def create_index() -> OperatorReviewIndex:
    return OperatorReviewIndex(
        index_id=f"IDX_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        artifacts=ARTIFACTS,
    )


def search_artifacts(index: OperatorReviewIndex, query: str) -> list[ReviewArtifact]:
    q = query.lower()
    return [a for a in index.artifacts if q in a.title.lower() or q in a.category.lower()]


def filter_by_category(index: OperatorReviewIndex, category: str) -> list[ReviewArtifact]:
    return [a for a in index.artifacts if a.category == category]


def write_index(index: OperatorReviewIndex, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index.to_dict(), indent=2), encoding="utf-8")


def render_report(index: OperatorReviewIndex) -> str:
    lines = ["# Operator Review Index", "",
        f"**index_id={index.index_id}**",
        "**MOCK_REVIEW_INDEX_ONLY**",
        "**REAL_TESTNET_SUBMIT_NOT_ALLOWED**", "",
        f"Total artifacts: {len(index.artifacts)}", "",
        "## Artifacts", "",
        "| ID | Category | Title | Status |",
        "|----|----------|-------|--------|"]
    for a in index.artifacts:
        lines.append(f"| {a.artifact_id} | {a.category} | {a.title} | {a.status} |")
    lines.extend(["", "## Conclusion", "", "OPERATOR_REVIEW_INDEX_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
