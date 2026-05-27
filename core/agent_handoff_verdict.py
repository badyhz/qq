"""Agent handoff verdict — frozen dataclass and build_verdict pure function.

T1395 — Pure, frozen, no I/O, no network, no random, no timestamps, no env reads.
"""

from dataclasses import dataclass
from typing import Tuple

from core.agent_handoff_safety_rule import AgentHandoffSafetyRule
from core.agent_handoff_test_spec import AgentHandoffTestSpec
from core.agent_handoff_commit_rule import AgentHandoffCommitRule


@dataclass(frozen=True)
class AgentHandoffVerdict:
    """Verdict on whether an agent handoff is acceptable."""

    verdict: str  # PASS / FAIL / WARN
    notes: str
    violations: Tuple[str, ...]
    warnings: Tuple[str, ...]


def build_verdict(
    safety_rules: Tuple[AgentHandoffSafetyRule, ...],
    test_specs: Tuple[AgentHandoffTestSpec, ...],
    commit_rules: Tuple[AgentHandoffCommitRule, ...],
) -> AgentHandoffVerdict:
    """Build a verdict from safety rules, test specs, and commit rules.

    Pure function — evaluates constraints and returns a frozen verdict.
    """
    violations: list = []
    warnings: list = []

    for rule in safety_rules:
        if rule.severity == "CRITICAL":
            violations.append(f"CRITICAL: {rule.rule_id} — {rule.description}")
        elif rule.severity == "WARNING":
            warnings.append(f"WARNING: {rule.rule_id} — {rule.description}")

    for spec in test_specs:
        if spec.mandatory and not spec.test_command:
            violations.append(f"MANDATORY_TEST_MISSING: {spec.spec_id}")

    for rule in commit_rules:
        if rule.required and not rule.pattern:
            violations.append(f"REQUIRED_COMMIT_RULE_EMPTY: {rule.rule_id}")

    if violations:
        verdict = "FAIL"
        notes = f"{len(violations)} violation(s), {len(warnings)} warning(s)"
    elif warnings:
        verdict = "WARN"
        notes = f"0 violations, {len(warnings)} warning(s)"
    else:
        verdict = "PASS"
        notes = "All checks passed"

    return AgentHandoffVerdict(
        verdict=verdict,
        notes=notes,
        violations=tuple(violations),
        warnings=tuple(warnings),
    )
