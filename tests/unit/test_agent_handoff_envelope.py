"""Tests for agent handoff envelope models and renderer.

T1399 — 11+ tests covering frozen dataclasses, immutability, verdict logic, rendering.
"""

import pytest

from core.agent_handoff_envelope import AgentHandoffEnvelope
from core.agent_handoff_safety_rule import AgentHandoffSafetyRule
from core.agent_handoff_test_spec import AgentHandoffTestSpec
from core.agent_handoff_commit_rule import AgentHandoffCommitRule
from core.agent_handoff_verdict import AgentHandoffVerdict, build_verdict
from core.agent_handoff_renderer import (
    render_handoff_envelope_md,
    render_safety_rule_md,
    render_test_spec_md,
    render_commit_rule_md,
    render_handoff_verdict_md,
)


# --- Envelope tests ---

def test_create_envelope_frozen():
    env = AgentHandoffEnvelope(
        envelope_id="E1",
        mission_summary="test mission",
        allowed_scope=("core/",),
        forbidden_paths=("core/live_runner.py",),
        test_commands=("pytest -v",),
        commit_rules=("no secrets",),
        safety_constraints=("dry-run only",),
    )
    assert env.envelope_id == "E1"
    assert env.mission_summary == "test mission"


def test_envelope_immutability():
    env = AgentHandoffEnvelope(
        envelope_id="E1",
        mission_summary="test",
        allowed_scope=(),
        forbidden_paths=(),
        test_commands=(),
        commit_rules=(),
        safety_constraints=(),
    )
    with pytest.raises(AttributeError):
        env.envelope_id = "E2"  # type: ignore[misc]


# --- Safety rule tests ---

def test_safety_rule_frozen():
    rule = AgentHandoffSafetyRule(
        rule_id="SR1",
        rule_type="FORBIDDEN_PATH",
        description="No live runner access",
        severity="CRITICAL",
    )
    assert rule.severity == "CRITICAL"


def test_safety_rule_immutability():
    rule = AgentHandoffSafetyRule(
        rule_id="SR1",
        rule_type="FORBIDDEN_PATH",
        description="test",
        severity="WARNING",
    )
    with pytest.raises(AttributeError):
        rule.severity = "CRITICAL"  # type: ignore[misc]


# --- Test spec tests ---

def test_test_spec_frozen():
    spec = AgentHandoffTestSpec(
        spec_id="TS1",
        test_command="pytest",
        expected_result="pass",
        timeout_seconds=120,
        mandatory=True,
    )
    assert spec.mandatory is True
    assert spec.timeout_seconds == 120


# --- Commit rule tests ---

def test_commit_rule_frozen():
    rule = AgentHandoffCommitRule(
        rule_id="CR1",
        pattern="feat: *",
        description="feat prefix required",
        required=True,
    )
    assert rule.required is True


# --- build_verdict tests ---

def test_build_verdict_pass():
    verdict = build_verdict(
        safety_rules=(
            AgentHandoffSafetyRule("SR1", "FORBIDDEN_PATH", "ok", "WARNING"),
        ),
        test_specs=(
            AgentHandoffTestSpec("TS1", "pytest", "pass", 60, True),
        ),
        commit_rules=(
            AgentHandoffCommitRule("CR1", "feat: *", "prefix", True),
        ),
    )
    # WARNING severity produces WARN, not PASS
    assert verdict.verdict == "WARN"
    assert len(verdict.warnings) == 1


def test_build_verdict_fail_critical():
    verdict = build_verdict(
        safety_rules=(
            AgentHandoffSafetyRule("SR1", "FORBIDDEN_PATH", "bad", "CRITICAL"),
        ),
        test_specs=(),
        commit_rules=(),
    )
    assert verdict.verdict == "FAIL"
    assert len(verdict.violations) == 1


def test_build_verdict_fail_missing_mandatory_test():
    verdict = build_verdict(
        safety_rules=(),
        test_specs=(
            AgentHandoffTestSpec("TS1", "", "pass", 60, True),
        ),
        commit_rules=(),
    )
    assert verdict.verdict == "FAIL"
    assert any("MANDATORY_TEST_MISSING" in v for v in verdict.violations)


def test_build_verdict_fail_empty_required_commit_rule():
    verdict = build_verdict(
        safety_rules=(),
        test_specs=(),
        commit_rules=(
            AgentHandoffCommitRule("CR1", "", "empty", True),
        ),
    )
    assert verdict.verdict == "FAIL"
    assert any("REQUIRED_COMMIT_RULE_EMPTY" in v for v in verdict.violations)


def test_build_verdict_pass_clean():
    verdict = build_verdict(
        safety_rules=(
            AgentHandoffSafetyRule("SR1", "REQUIRED_CHECK", "ok", "INFO"),
        ),
        test_specs=(
            AgentHandoffTestSpec("TS1", "pytest", "pass", 60, False),
        ),
        commit_rules=(
            AgentHandoffCommitRule("CR1", "feat: *", "prefix", False),
        ),
    )
    assert verdict.verdict == "PASS"


# --- Renderer tests ---

def test_render_envelope_md():
    env = AgentHandoffEnvelope(
        envelope_id="E1",
        mission_summary="test",
        allowed_scope=("core/",),
        forbidden_paths=("core/live_runner.py",),
        test_commands=("pytest -v",),
        commit_rules=("no secrets",),
        safety_constraints=("dry-run",),
    )
    md = render_handoff_envelope_md(env)
    assert "E1" in md
    assert "core/" in md
    assert "live_runner" in md


def test_render_safety_rule_md():
    rule = AgentHandoffSafetyRule("SR1", "FORBIDDEN_PATH", "desc", "CRITICAL")
    md = render_safety_rule_md(rule)
    assert "SR1" in md
    assert "CRITICAL" in md


def test_render_test_spec_md():
    spec = AgentHandoffTestSpec("TS1", "pytest", "pass", 60, True)
    md = render_test_spec_md(spec)
    assert "TS1" in md
    assert "pytest" in md
    assert "Yes" in md


def test_render_commit_rule_md():
    rule = AgentHandoffCommitRule("CR1", "feat: *", "prefix", True)
    md = render_commit_rule_md(rule)
    assert "CR1" in md
    assert "feat: *" in md


def test_render_verdict_md():
    verdict = AgentHandoffVerdict("FAIL", "has violations", ("v1",), ("w1",))
    md = render_handoff_verdict_md(verdict)
    assert "FAIL" in md
    assert "v1" in md
    assert "w1" in md


def test_render_verdict_md_no_violations():
    verdict = AgentHandoffVerdict("PASS", "clean", (), ())
    md = render_handoff_verdict_md(verdict)
    assert "PASS" in md
    assert "Violations" not in md
