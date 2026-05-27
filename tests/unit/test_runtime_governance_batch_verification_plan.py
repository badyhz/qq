"""T823 — Tests for runtime governance batch verification plan."""
from core.runtime_governance_batch_verification_plan import (
    VerificationCommand,
    build_runtime_governance_batch_verification_plan,
    verification_plan_to_dict,
    verification_plan_to_markdown,
)


def test_plan_has_five_commands():
    plan = build_runtime_governance_batch_verification_plan()
    assert len(plan) == 5


def test_commands_include_runtime_governance():
    plan = build_runtime_governance_batch_verification_plan()
    ids = [c.command_id for c in plan]
    assert "runtime_governance_tests" in ids


def test_core_regression_present():
    plan = build_runtime_governance_batch_verification_plan()
    ids = [c.command_id for c in plan]
    assert "core_regression" in ids


def test_markdown_deterministic():
    plan = build_runtime_governance_batch_verification_plan()
    md1 = verification_plan_to_markdown(plan)
    md2 = verification_plan_to_markdown(plan)
    assert md1 == md2


def test_dict_deterministic():
    plan = build_runtime_governance_batch_verification_plan()
    d1 = verification_plan_to_dict(plan)
    d2 = verification_plan_to_dict(plan)
    assert d1 == d2
