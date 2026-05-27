"""T1124 - Human Review Verdict Renderer."""
from __future__ import annotations

from core.human_review_gate_verdict import HumanReviewGateVerdict
from core.human_review_rejection_state import HumanReviewRejectionState
from core.human_review_gate_model_closeout import HumanReviewGateModelCloseout


def render_verdict_detail_md(verdict: HumanReviewGateVerdict) -> str:
    lines: list[str] = []
    lines.append("## Verdict Detail")
    lines.append("")
    lines.append(f"- **Gate ID:** {verdict.gate_id}")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append("")
    if verdict.issues:
        lines.append("### Issues")
        for issue in verdict.issues:
            lines.append(f"- {issue}")
        lines.append("")
    if verdict.notes:
        lines.append("### Notes")
        for note in verdict.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def render_rejection_state_md(state: HumanReviewRejectionState) -> str:
    lines: list[str] = []
    lines.append("## Rejection State")
    lines.append("")
    lines.append(f"- **State:** {state.state}")
    lines.append(f"- **Gate ID:** {state.gate_id}")
    lines.append(f"- **Rejector:** {state.rejector}")
    lines.append(f"- **Reason:** {state.reason}")
    lines.append(f"- **Revision Allowed:** {state.revision_allowed}")
    lines.append("")
    return "\n".join(lines)


def render_closeout_md(closeout: HumanReviewGateModelCloseout) -> str:
    lines: list[str] = []
    lines.append("## Human Review Gate Model Closeout")
    lines.append("")
    lines.append(f"- **Model Count:** {closeout.model_count}")
    lines.append(f"- **Verdict:** {closeout.verdict}")
    lines.append("")
    if closeout.models:
        lines.append("### Models")
        for model in closeout.models:
            lines.append(f"- {model}")
        lines.append("")
    return "\n".join(lines)
