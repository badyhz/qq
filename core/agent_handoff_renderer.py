"""Agent handoff renderer — pure markdown rendering functions.

T1396 — Pure functions, no I/O, no side effects.
"""

from core.agent_handoff_envelope import AgentHandoffEnvelope
from core.agent_handoff_safety_rule import AgentHandoffSafetyRule
from core.agent_handoff_test_spec import AgentHandoffTestSpec
from core.agent_handoff_commit_rule import AgentHandoffCommitRule
from core.agent_handoff_verdict import AgentHandoffVerdict


def render_handoff_envelope_md(envelope: AgentHandoffEnvelope) -> str:
    """Render an AgentHandoffEnvelope to markdown."""
    lines = [
        f"# Agent Handoff Envelope: {envelope.envelope_id}",
        "",
        f"**Mission:** {envelope.mission_summary}",
        "",
        "## Allowed Scope",
    ]
    for item in envelope.allowed_scope:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Forbidden Paths")
    for item in envelope.forbidden_paths:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Test Commands")
    for item in envelope.test_commands:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Commit Rules")
    for item in envelope.commit_rules:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Safety Constraints")
    for item in envelope.safety_constraints:
        lines.append(f"- {item}")
    return "\n".join(lines)


def render_safety_rule_md(rule: AgentHandoffSafetyRule) -> str:
    """Render an AgentHandoffSafetyRule to markdown."""
    return (
        f"| {rule.rule_id} | {rule.rule_type} | {rule.severity} "
        f"| {rule.description} |"
    )


def render_test_spec_md(spec: AgentHandoffTestSpec) -> str:
    """Render an AgentHandoffTestSpec to markdown."""
    mandatory_str = "Yes" if spec.mandatory else "No"
    return (
        f"| {spec.spec_id} | `{spec.test_command}` | {spec.expected_result} "
        f"| {spec.timeout_seconds}s | {mandatory_str} |"
    )


def render_commit_rule_md(rule: AgentHandoffCommitRule) -> str:
    """Render an AgentHandoffCommitRule to markdown."""
    required_str = "Yes" if rule.required else "No"
    return (
        f"| {rule.rule_id} | `{rule.pattern}` | {rule.description} "
        f"| {required_str} |"
    )


def render_handoff_verdict_md(verdict: AgentHandoffVerdict) -> str:
    """Render an AgentHandoffVerdict to markdown."""
    lines = [
        "# Agent Handoff Verdict",
        "",
        f"**Verdict:** {verdict.verdict}",
        f"**Notes:** {verdict.notes}",
        "",
    ]
    if verdict.violations:
        lines.append("## Violations")
        for v in verdict.violations:
            lines.append(f"- {v}")
        lines.append("")
    if verdict.warnings:
        lines.append("## Warnings")
        for w in verdict.warnings:
            lines.append(f"- {w}")
        lines.append("")
    return "\n".join(lines)
