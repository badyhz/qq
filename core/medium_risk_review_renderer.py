from __future__ import annotations

from core.medium_risk_review import MediumRiskReview
from core.medium_risk_script_kind import MediumRiskScriptKind
from core.medium_risk_review_verdict import MediumRiskReviewVerdict
from core.medium_risk_model_closeout import MediumRiskModelCloseout


def render_medium_risk_review_md(review: MediumRiskReview) -> str:
    """Render a MediumRiskReview as markdown."""
    lines = ("# Medium Risk Review", "")
    lines += (f"- **Review ID:** {review.review_id}",)
    lines += (f"- **Verdict:** {review.verdict}",)
    if review.scripts:
        lines += ("", "## Scripts",)
        for s in review.scripts:
            lines += (f"- {s}",)
    if review.policies:
        lines += ("", "## Policies",)
        for p in review.policies:
            lines += (f"- {p}",)
    return "\n".join(lines)


def render_medium_risk_script_kind_md(kind: MediumRiskScriptKind) -> str:
    """Render a MediumRiskScriptKind as markdown."""
    lines = ("# Medium Risk Script Kind", "")
    lines += (f"- **OPERATIONAL:** {kind.OPERATIONAL}",)
    lines += (f"- **VERIFICATION:** {kind.VERIFICATION}",)
    lines += (f"- **SHADOW:** {kind.SHADOW}",)
    lines += (f"- **TESTNET:** {kind.TESTNET}",)
    lines += (f"- **REMEDIATION:** {kind.REMEDIATION}",)
    return "\n".join(lines)


def render_medium_risk_verdict_md(verdict: MediumRiskReviewVerdict) -> str:
    """Render a MediumRiskReviewVerdict as markdown."""
    lines = ("# Medium Risk Review Verdict", "")
    lines += (f"- **Verdict:** {verdict.verdict}",)
    if verdict.issues:
        lines += ("", "## Issues",)
        for i in verdict.issues:
            lines += (f"- {i}",)
    if verdict.notes:
        lines += ("", "## Notes",)
        for n in verdict.notes:
            lines += (f"- {n}",)
    return "\n".join(lines)


def render_medium_risk_closeout_md(closeout: MediumRiskModelCloseout) -> str:
    """Render a MediumRiskModelCloseout as markdown."""
    lines = ("# Medium Risk Model Closeout", "")
    lines += (f"- **Model count:** {closeout.model_count}",)
    lines += (f"- **Verdict:** {closeout.verdict}",)
    if closeout.models:
        lines += ("", "## Models",)
        for m in closeout.models:
            lines += (f"- {m}",)
    return "\n".join(lines)
