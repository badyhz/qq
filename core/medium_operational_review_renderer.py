"""T1342 - Medium Operational Review Renderer."""
from __future__ import annotations

from core.medium_operational_review import MediumOperationalReview
from core.medium_operational_command_policy import MediumOperationalCommandPolicy
from core.medium_operational_artifact_policy import MediumOperationalArtifactPolicy
from core.medium_operational_review_verdict import MediumOperationalReviewVerdict


def render_medium_operational_review_md(review: MediumOperationalReview) -> str:
    """Render MediumOperationalReview to markdown."""
    lines: list[str] = []
    lines.append("## Medium Operational Review")
    lines.append("")
    lines.append(f"- **Review ID:** {review.review_id}")
    lines.append(f"- **Verdict:** {review.verdict}")
    lines.append(f"- **Script Count:** {review.script_count()}")
    lines.append(f"- **Policy Count:** {review.policy_count()}")
    lines.append("")
    if review.scripts:
        lines.append("### Scripts")
        for script in review.scripts:
            lines.append(f"- {script}")
        lines.append("")
    if review.policies:
        lines.append("### Policies")
        for policy in review.policies:
            lines.append(f"- {policy}")
        lines.append("")
    return "\n".join(lines)


def render_medium_operational_command_policy_md(policy: MediumOperationalCommandPolicy) -> str:
    """Render MediumOperationalCommandPolicy to markdown."""
    lines: list[str] = []
    lines.append("## Medium Operational Command Policy")
    lines.append("")
    lines.append(f"- **Policy ID:** {policy.policy_id}")
    lines.append(f"- **Dry Run Only:** {policy.dry_run_only}")
    lines.append(f"- **Allowed Count:** {policy.allowed_count()}")
    lines.append(f"- **Forbidden Count:** {policy.forbidden_count()}")
    lines.append("")
    if policy.allowed_commands:
        lines.append("### Allowed Commands")
        for cmd in policy.allowed_commands:
            lines.append(f"- `{cmd}`")
        lines.append("")
    if policy.forbidden_commands:
        lines.append("### Forbidden Commands")
        for cmd in policy.forbidden_commands:
            lines.append(f"- `{cmd}`")
        lines.append("")
    return "\n".join(lines)


def render_medium_operational_artifact_policy_md(policy: MediumOperationalArtifactPolicy) -> str:
    """Render MediumOperationalArtifactPolicy to markdown."""
    lines: list[str] = []
    lines.append("## Medium Operational Artifact Policy")
    lines.append("")
    lines.append(f"- **Policy ID:** {policy.policy_id}")
    lines.append(f"- **Allowed Paths Count:** {policy.allowed_count()}")
    lines.append(f"- **Forbidden Paths Count:** {policy.forbidden_count()}")
    lines.append("")
    if policy.allowed_write_paths:
        lines.append("### Allowed Write Paths")
        for path in policy.allowed_write_paths:
            lines.append(f"- `{path}`")
        lines.append("")
    if policy.forbidden_write_paths:
        lines.append("### Forbidden Write Paths")
        for path in policy.forbidden_write_paths:
            lines.append(f"- `{path}`")
        lines.append("")
    return "\n".join(lines)


def render_medium_operational_verdict_md(verdict: MediumOperationalReviewVerdict) -> str:
    """Render MediumOperationalReviewVerdict to markdown."""
    lines: list[str] = []
    lines.append("## Medium Operational Review Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append(f"- **Violation Count:** {verdict.violation_count()}")
    if verdict.notes:
        lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    if verdict.violations:
        lines.append("### Violations")
        for v in verdict.violations:
            lines.append(f"- {v}")
        lines.append("")
    return "\n".join(lines)
