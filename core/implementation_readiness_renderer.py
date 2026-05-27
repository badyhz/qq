from __future__ import annotations

from core.implementation_readiness_scoring import ImplementationReadinessScoring
from core.readiness_score_dimension import ReadinessScoreDimension
from core.readiness_blocker import ReadinessBlocker
from core.readiness_scoring_verdict import ReadinessScoringVerdict


def render_readiness_scoring_md(scoring: ImplementationReadinessScoring) -> str:
    """Render an ImplementationReadinessScoring as markdown."""
    lines = ("# Implementation Readiness Scoring", "")
    lines += (f"- **Scoring ID:** {scoring.scoring_id}",)
    dim_count = len(scoring.dimensions) if hasattr(scoring.dimensions, '__len__') else 0
    blocker_count = len(scoring.blockers) if hasattr(scoring.blockers, '__len__') else 0
    lines += (f"- **Dimensions:** {dim_count}",)
    lines += (f"- **Blockers:** {blocker_count}",)
    verdict_val = getattr(scoring.verdict, 'verdict', scoring.verdict)
    lines += (f"- **Verdict:** {verdict_val}",)
    hold_val = getattr(scoring.hold_state, 'value', getattr(scoring.hold_state, 'hold', scoring.hold_state))
    lines += (f"- **Hold state:** {hold_val}",)
    return "\n".join(lines)


def render_readiness_dimension_md(dim: ReadinessScoreDimension) -> str:
    """Render a ReadinessScoreDimension as markdown."""
    lines = ("# Readiness Score Dimension", "")
    lines += (f"- **Name:** {dim.value}",)
    lines += (f"- **Weight:** {dim.weight()}",)
    lines += (f"- **Threshold:** {dim.threshold()}",)
    return "\n".join(lines)


def render_readiness_blocker_md(blocker: ReadinessBlocker) -> str:
    """Render a ReadinessBlocker as markdown."""
    lines = ("# Readiness Blocker", "")
    lines += (f"- **ID:** {blocker.blocker_id}",)
    lines += (f"- **Type:** {blocker.blocker_type.value}",)
    lines += (f"- **Severity:** {blocker.severity.value}",)
    lines += (f"- **Description:** {blocker.description}",)
    lines += (f"- **Resolution:** {blocker.resolution_path}",)
    return "\n".join(lines)


def render_readiness_verdict_md(verdict: ReadinessScoringVerdict) -> str:
    """Render a ReadinessScoringVerdict as markdown."""
    lines = ("# Readiness Scoring Verdict", "")
    lines += (f"- **Verdict:** {verdict.verdict.value}",)
    lines += (f"- **Score %:** {verdict.score_pct}",)
    lines += (f"- **Notes:** {verdict.notes}",)
    blocker_count = len(verdict.blockers) if hasattr(verdict.blockers, '__len__') else 0
    lines += (f"- **Blockers:** {blocker_count}",)
    return "\n".join(lines)
