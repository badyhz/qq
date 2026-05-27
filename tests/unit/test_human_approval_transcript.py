"""T1457 - Tests for human approval transcript, steps, and renderer."""
from __future__ import annotations

import pytest

from core.human_approval_transcript import HumanApprovalTranscript
from core.human_approval_transcript_renderer import (
    render_readiness_dimension_md,
    render_readiness_score_md,
    render_transcript_md,
    render_transcript_step_md,
)
from core.promotion_readiness_calculator import calculate_readiness
from core.promotion_readiness_dimension import (
    PromotionReadinessDimension,
    ReadinessDimensionName,
)
from core.transcript_step import StepType, TranscriptStep


# ── StepType enum ───────────────────────────────────────────────────────


def test_step_type_enum_values():
    expected = {
        "REVIEW_START",
        "CHECK_PASS",
        "CHECK_FAIL",
        "EVIDENCE_COLLECTED",
        "RISK_ACKNOWLEDGED",
        "DECISION_MADE",
    }
    actual = {v.value for v in StepType}
    assert actual == expected


# ── TranscriptStep frozen ──────────────────────────────────────────────


def test_step_frozen_immutable():
    step = TranscriptStep(
        step_id="st1",
        step_type=StepType.REVIEW_START,
        description="begin review",
        step_data="init",
    )
    with pytest.raises(AttributeError):
        step.description = "changed"  # type: ignore[misc]


def test_step_with_dict_data():
    step = TranscriptStep(
        step_id="st1",
        step_type=StepType.CHECK_PASS,
        description="import safe",
        step_data={"check": "import", "result": "pass"},
    )
    assert isinstance(step.step_data, dict)
    assert step.step_data["check"] == "import"


def test_step_with_string_data():
    step = TranscriptStep(
        step_id="st2",
        step_type=StepType.CHECK_FAIL,
        description="network unsafe",
        step_data="found socket.connect call",
    )
    assert isinstance(step.step_data, str)


# ── HumanApprovalTranscript frozen ─────────────────────────────────────


def test_transcript_frozen_immutable():
    t = HumanApprovalTranscript(
        transcript_id="t1",
        file_path="core/foo.py",
        reviewer_id="alice",
        steps=(),
        final_decision="APPROVED",
        timestamp_iso="2026-05-28T00:00:00Z",
    )
    with pytest.raises(AttributeError):
        t.final_decision = "REJECTED"  # type: ignore[misc]


def test_transcript_fields():
    steps = (
        TranscriptStep("s1", StepType.REVIEW_START, "start", "ok"),
        TranscriptStep("s2", StepType.DECISION_MADE, "decided", "APPROVED"),
    )
    t = HumanApprovalTranscript(
        transcript_id="t1",
        file_path="core/bar.py",
        reviewer_id="bob",
        steps=steps,
        final_decision="APPROVED",
        timestamp_iso="2026-05-28T12:00:00Z",
    )
    assert t.transcript_id == "t1"
    assert t.file_path == "core/bar.py"
    assert t.reviewer_id == "bob"
    assert len(t.steps) == 2
    assert t.final_decision == "APPROVED"
    assert t.timestamp_iso == "2026-05-28T12:00:00Z"


# ── Renderer ────────────────────────────────────────────────────────────


def test_render_transcript_step_md_dict():
    step = TranscriptStep(
        step_id="s1",
        step_type=StepType.EVIDENCE_COLLECTED,
        description="collected evidence",
        step_data={"file": "foo.py", "lines": 42},
    )
    md = render_transcript_step_md(step, 1)
    assert "Step 1" in md
    assert "EVIDENCE_COLLECTED" in md
    assert "collected evidence" in md
    assert "file: foo.py" in md


def test_render_transcript_step_md_string():
    step = TranscriptStep(
        step_id="s2",
        step_type=StepType.RISK_ACKNOWLEDGED,
        description="risk noted",
        step_data="high risk",
    )
    md = render_transcript_step_md(step, 3)
    assert "Step 3" in md
    assert "RISK_ACKNOWLEDGED" in md
    assert "high risk" in md


def test_render_transcript_md_full():
    steps = (
        TranscriptStep("s1", StepType.REVIEW_START, "begin", "ok"),
        TranscriptStep("s2", StepType.DECISION_MADE, "done", "APPROVED"),
    )
    t = HumanApprovalTranscript(
        transcript_id="t1",
        file_path="core/foo.py",
        reviewer_id="carol",
        steps=steps,
        final_decision="APPROVED",
        timestamp_iso="2026-05-28T00:00:00Z",
    )
    md = render_transcript_md(t)
    assert "# Human Approval Transcript" in md
    assert "carol" in md
    assert "APPROVED" in md
    assert "Step 1" in md
    assert "Step 2" in md


def test_render_readiness_score_md():
    score = calculate_readiness("core/foo.py", "MEDIUM")
    md = render_readiness_score_md(score)
    assert "# Promotion Readiness Score" in md
    assert "core/foo.py" in md
    assert "READY" in md
    assert "IMPORT_SAFETY" in md
    assert "NETWORK_SAFETY" in md


def test_render_readiness_dimension_md():
    dim = PromotionReadinessDimension(
        dimension_id="d1",
        name=ReadinessDimensionName.CREDENTIAL_SAFETY,
        weight=0.20,
        score=0.9,
        max_score=1.0,
    )
    md = render_readiness_dimension_md(dim, 2)
    assert "CREDENTIAL_SAFETY" in md
    assert "0.20" in md
    assert "90%" in md
