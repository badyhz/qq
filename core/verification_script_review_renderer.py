"""T1343 - Verification Script Review Renderer."""
from __future__ import annotations

from core.verification_script_review import VerificationScriptReview
from core.verification_script_import_policy import VerificationScriptImportPolicy
from core.verification_script_dry_run_proof import VerificationScriptDryRunProof
from core.verification_script_review_verdict import VerificationScriptReviewVerdict


def render_verification_script_review_md(review: VerificationScriptReview) -> str:
    """Render VerificationScriptReview to markdown."""
    lines: list[str] = []
    lines.append("## Verification Script Review")
    lines.append("")
    lines.append(f"- **Review ID:** {review.review_id}")
    lines.append(f"- **Script Name:** {review.script_name}")
    lines.append(f"- **Verdict:** {review.verdict}")
    lines.append(f"- **Check Count:** {review.check_count()}")
    lines.append("")
    if review.checks:
        lines.append("### Checks")
        for check in review.checks:
            lines.append(f"- {check}")
        lines.append("")
    return "\n".join(lines)


def render_verification_script_import_policy_md(policy: VerificationScriptImportPolicy) -> str:
    """Render VerificationScriptImportPolicy to markdown."""
    lines: list[str] = []
    lines.append("## Verification Script Import Policy")
    lines.append("")
    lines.append(f"- **Policy ID:** {policy.policy_id}")
    lines.append(f"- **Allowed Count:** {policy.allowed_count()}")
    lines.append(f"- **Forbidden Count:** {policy.forbidden_count()}")
    lines.append("")
    if policy.allowed_imports:
        lines.append("### Allowed Imports")
        for imp in policy.allowed_imports:
            lines.append(f"- `{imp}`")
        lines.append("")
    if policy.forbidden_imports:
        lines.append("### Forbidden Imports")
        for imp in policy.forbidden_imports:
            lines.append(f"- `{imp}`")
        lines.append("")
    if policy.high_risk_patterns:
        lines.append("### High Risk Patterns")
        for pat in policy.high_risk_patterns:
            lines.append(f"- `{pat}`")
        lines.append("")
    return "\n".join(lines)


def render_verification_script_dry_run_proof_md(proof: VerificationScriptDryRunProof) -> str:
    """Render VerificationScriptDryRunProof to markdown."""
    lines: list[str] = []
    lines.append("## Verification Script Dry Run Proof")
    lines.append("")
    lines.append(f"- **Proof ID:** {proof.proof_id}")
    lines.append(f"- **Script Name:** {proof.script_name}")
    lines.append(f"- **Proof Type:** {proof.proof_type}")
    lines.append(f"- **Evidence Count:** {proof.evidence_count()}")
    lines.append("")
    if proof.evidence_refs:
        lines.append("### Evidence References")
        for ref in proof.evidence_refs:
            lines.append(f"- {ref}")
        lines.append("")
    return "\n".join(lines)


def render_verification_script_verdict_md(verdict: VerificationScriptReviewVerdict) -> str:
    """Render VerificationScriptReviewVerdict to markdown."""
    lines: list[str] = []
    lines.append("## Verification Script Review Verdict")
    lines.append("")
    lines.append(f"- **Verdict:** {verdict.verdict}")
    lines.append(f"- **Failure Count:** {verdict.failure_count()}")
    if verdict.notes:
        lines.append(f"- **Notes:** {verdict.notes}")
    lines.append("")
    if verdict.failed_checks:
        lines.append("### Failed Checks")
        for check in verdict.failed_checks:
            lines.append(f"- {check}")
        lines.append("")
    return "\n".join(lines)
