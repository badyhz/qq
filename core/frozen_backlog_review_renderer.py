"""T1341 - Frozen Backlog Review Renderer."""
from __future__ import annotations

from core.frozen_backlog_review import FrozenBacklogReview
from core.frozen_backlog_item_kind import FrozenBacklogItemKind
from core.frozen_backlog_review_state import FrozenBacklogReviewState
from core.frozen_backlog_denial_reason import FrozenBacklogDenialReason
from core.frozen_backlog_review_verdict import FrozenBacklogReviewVerdict


def render_frozen_backlog_review_md(review: FrozenBacklogReview) -> str:
    """Render FrozenBacklogReview to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Review")
    lines.append("")
    lines.append(f"- **Review ID:** {review.review_id}")
    lines.append(f"- **State:** {review.review_state.state}")
    lines.append(f"- **Item Count:** {len(review.backlog_items)}")
    lines.append("")
    if review.backlog_items:
        lines.append("### Backlog Items")
        for item in review.backlog_items:
            lines.append(f"- {item}")
        lines.append("")
    if review.verdict:
        lines.append(render_frozen_backlog_review_verdict_md(review.verdict))
    return "\n".join(lines)


def render_frozen_backlog_item_kind_md(kind: FrozenBacklogItemKind) -> str:
    """Render FrozenBacklogItemKind to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Item Kind")
    lines.append("")
    lines.append(f"- **Kind:** {kind.kind}")
    lines.append("")
    return "\n".join(lines)


def render_frozen_backlog_review_state_md(state: FrozenBacklogReviewState) -> str:
    """Render FrozenBacklogReviewState to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Review State")
    lines.append("")
    lines.append(f"- **State:** {state.state}")
    lines.append("")
    return "\n".join(lines)


def render_frozen_backlog_denial_reason_md(reason: FrozenBacklogDenialReason) -> str:
    """Render FrozenBacklogDenialReason to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Denial Reason")
    lines.append("")
    lines.append(f"- **Reason ID:** {reason.reason_id}")
    lines.append(f"- **Category:** {reason.category}")
    lines.append(f"- **Description:** {reason.description}")
    lines.append(f"- **Severity:** {reason.severity}")
    lines.append("")
    return "\n".join(lines)


def render_frozen_backlog_review_verdict_md(verdict: FrozenBacklogReviewVerdict) -> str:
    """Render FrozenBacklogReviewVerdict to markdown."""
    lines: list[str] = []
    lines.append("## Frozen Backlog Review Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    if verdict.notes:
        lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    if verdict.denial_reasons:
        lines.append("### Denial Reasons")
        for reason in verdict.denial_reasons:
            lines.append(f"- [{reason.reason_id}] {reason.category}: {reason.description} (severity={reason.severity})")
        lines.append("")
    if verdict.approvals:
        lines.append("### Approvals")
        for approval in verdict.approvals:
            lines.append(f"- [{approval.approval_id}] {approval.reviewer}: {approval.decision}")
        lines.append("")
    return "\n".join(lines)
