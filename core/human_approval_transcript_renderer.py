"""T1455 - Human approval transcript and readiness score renderers.

Pure functions. No I/O. No timestamps. No network.
"""
from __future__ import annotations

from typing import List

from core.human_approval_transcript import HumanApprovalTranscript
from core.promotion_readiness_dimension import PromotionReadinessDimension
from core.promotion_readiness_score import PromotionReadinessScore
from core.transcript_step import TranscriptStep


def render_transcript_step_md(step: TranscriptStep, index: int) -> str:
    """Render a single transcript step as markdown.

    Pure. No I/O.
    """
    lines: List[str] = [
        f"### Step {index}: {step.step_type.value}",
        "",
        f"**ID:** {step.step_id}",
        f"**Description:** {step.description}",
    ]
    if isinstance(step.step_data, dict):
        lines.append("")
        lines.append("**Data:**")
        for k, v in step.step_data.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append(f"**Data:** {step.step_data}")
    return "\n".join(lines)


def render_transcript_md(transcript: HumanApprovalTranscript) -> str:
    """Render a full transcript as markdown.

    Pure. No I/O.
    """
    lines: List[str] = [
        "# Human Approval Transcript",
        "",
        f"**Transcript ID:** {transcript.transcript_id}",
        f"**File:** {transcript.file_path}",
        f"**Reviewer:** {transcript.reviewer_id}",
        f"**Decision:** {transcript.final_decision}",
        f"**Timestamp:** {transcript.timestamp_iso}",
        "",
        "## Steps",
        "",
    ]
    for i, step in enumerate(transcript.steps, 1):
        lines.append(render_transcript_step_md(step, i))
        lines.append("")
    return "\n".join(lines)


def render_readiness_dimension_md(
    dim: PromotionReadinessDimension, index: int
) -> str:
    """Render a single readiness dimension as markdown.

    Pure. No I/O.
    """
    ratio = dim.score / dim.max_score if dim.max_score else 0.0
    return (
        f"| {index} | {dim.name.value} | {dim.weight:.2f} "
        f"| {dim.score:.2f} | {dim.max_score:.2f} | {ratio:.0%} |"
    )


def render_readiness_score_md(score: PromotionReadinessScore) -> str:
    """Render a readiness score as markdown.

    Pure. No I/O.
    """
    status = "READY" if score.is_ready else "NOT READY"
    lines: List[str] = [
        "# Promotion Readiness Score",
        "",
        f"**Score ID:** {score.score_id}",
        f"**File:** {score.file_path}",
        f"**Overall:** {score.overall_score:.4f}",
        f"**Threshold:** {score.threshold:.2f}",
        f"**Status:** {status}",
        "",
        "## Dimensions",
        "",
        "| # | Dimension | Weight | Score | Max | Ratio |",
        "|---|---|---|---|---|---|",
    ]
    for i, dim in enumerate(score.dimensions, 1):
        lines.append(render_readiness_dimension_md(dim, i))
    return "\n".join(lines)
