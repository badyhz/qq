"""Readiness scorecard."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ReadinessDimension:
    dimension_id: str
    name: str
    score: int  # 0-100
    status: str
    notes: str
    def to_dict(self) -> dict:
        return {"dimension_id": self.dimension_id, "name": self.name, "score": self.score, "status": self.status, "notes": self.notes}


@dataclass(frozen=True)
class ReadinessScorecard:
    scorecard_id: str
    created_at: str
    dimensions: tuple[ReadinessDimension, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"scorecard_id": self.scorecard_id, "created_at": self.created_at, "dimensions": [d.to_dict() for d in self.dimensions], "final_verdict": self.final_verdict}


DIMENSIONS = (
    ReadinessDimension("DIM_001", "mock_spec_readiness", 95, "READY", "Adapter spec, credential vault, signing, transport fully documented"),
    ReadinessDimension("DIM_002", "mock_transport_readiness", 90, "READY", "Mock transport contract, vault stub, adapter skeleton complete"),
    ReadinessDimension("DIM_003", "mock_replay_readiness", 90, "READY", "13 scenarios replayed, evidence bundle, approval packet v3 complete"),
    ReadinessDimension("DIM_004", "mock_review_readiness", 85, "READY", "Evidence browser, comparator, operator index, navigation report complete"),
    ReadinessDimension("DIM_005", "governance_readiness", 75, "PARTIAL", "Governance checklists documented, blockers present, approval packets generated"),
    ReadinessDimension("DIM_006", "operator_readiness", 70, "PARTIAL", "Operator runbook and review index available, manual approval not yet obtained"),
    ReadinessDimension("DIM_007", "credential_readiness", 10, "NOT_READY", "Only placeholder/stub credentials, no real credential review"),
    ReadinessDimension("DIM_008", "exchange_permission_readiness", 5, "NOT_READY", "No real exchange permission review, only documented requirements"),
    ReadinessDimension("DIM_009", "real_testnet_readiness", 0, "NOT_READY", "No real testnet adapter implemented, no read-only discovery"),
    ReadinessDimension("DIM_010", "real_submit_readiness", 0, "NOT_READY", "Submit gate locked, no approval, no real adapter, no real credentials"),
)


def create_scorecard() -> ReadinessScorecard:
    return ReadinessScorecard(
        scorecard_id=f"RSC_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        dimensions=DIMENSIONS,
        final_verdict="MOCK_READY|REAL_TESTNET_NOT_READY|SUBMIT_UNLOCK_BLOCKED",
    )


def average_score(scorecard: ReadinessScorecard) -> float:
    if not scorecard.dimensions:
        return 0.0
    return round(sum(d.score for d in scorecard.dimensions) / len(scorecard.dimensions), 1)


def mock_readiness(scorecard: ReadinessScorecard) -> int:
    mock_dims = [d for d in scorecard.dimensions if "mock" in d.name]
    if not mock_dims:
        return 0
    return round(sum(d.score for d in mock_dims) / len(mock_dims))


def real_readiness(scorecard: ReadinessScorecard) -> int:
    real_dims = [d for d in scorecard.dimensions if "real" in d.name]
    if not real_dims:
        return 0
    return round(sum(d.score for d in real_dims) / len(real_dims))


def write_scorecard(scorecard: ReadinessScorecard, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scorecard.to_dict(), indent=2), encoding="utf-8")


def render_report(scorecard: ReadinessScorecard) -> str:
    lines = ["# Readiness Scorecard", "",
        f"**scorecard_id={scorecard.scorecard_id}**",
        f"**average_score={average_score(scorecard)}**",
        f"**mock_readiness={mock_readiness(scorecard)}**",
        f"**real_readiness={real_readiness(scorecard)}**",
        f"**final_verdict={scorecard.final_verdict}**",
        "**REAL_TRADING_NOT_ALLOWED**", "",
        "## Dimensions", "",
        "| Dimension | Score | Status | Notes |",
        "|-----------|-------|--------|-------|"]
    for d in scorecard.dimensions:
        lines.append(f"| {d.name} | {d.score} | {d.status} | {d.notes} |")
    lines.extend(["", "## Conclusion", "",
        "READINESS_SCORECARD_READY",
        "REAL_TESTNET_NOT_READY",
        "SUBMIT_UNLOCK_BLOCKED",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
