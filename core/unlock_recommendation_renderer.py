"""T1461 - Unlock recommendation markdown renderer. Pure functions."""
from __future__ import annotations

from core.unlock_recommendation import UnlockRecommendation


def render_unlock_recommendation_md(rec: UnlockRecommendation) -> str:
    """Render UnlockRecommendation to markdown."""
    lines: list[str] = []
    lines.append("## Unlock Recommendation")
    lines.append("")
    lines.append(f"- **ID:** {rec.recommendation_id}")
    lines.append(f"- **File:** {rec.file_path}")
    lines.append(f"- **Risk Class:** {rec.risk_class}")
    lines.append(f"- **Readiness Score:** {rec.readiness_score:.2f}")
    lines.append(f"- **Recommendation:** {rec.recommendation}")
    lines.append("")
    if rec.conditions:
        lines.append(render_recommendation_conditions_md(rec))
    if rec.blockers:
        lines.append(render_recommendation_blockers_md(rec))
    return "\n".join(lines)


def render_recommendation_conditions_md(rec: UnlockRecommendation) -> str:
    """Render recommendation conditions to markdown."""
    lines: list[str] = []
    lines.append("### Conditions")
    lines.append("")
    for c in rec.conditions:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def render_recommendation_blockers_md(rec: UnlockRecommendation) -> str:
    """Render recommendation blockers to markdown."""
    lines: list[str] = []
    lines.append("### Blockers")
    lines.append("")
    for b in rec.blockers:
        lines.append(f"- {b}")
    lines.append("")
    return "\n".join(lines)
