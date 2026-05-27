"""T851 tests — Runtime governance read-only verification command plan."""
import pytest

from core.runtime_governance_readonly_verification_command_plan import (
    RuntimeGovernanceReadOnlyVerificationCommand,
    build_readonly_verification_command_plan,
    readonly_verification_command_plan_to_dict,
    readonly_verification_command_plan_to_markdown,
)


class TestBuildReadonlyVerificationCommandPlan:
    def test_returns_five_commands(self):
        plan = build_readonly_verification_command_plan()
        assert len(plan) == 5

    def test_all_required_except_last(self):
        plan = build_readonly_verification_command_plan()
        for cmd in plan[:-1]:
            assert cmd.required is True
        assert plan[-1].required is False

    def test_commands_avoid_heredoc(self):
        plan = build_readonly_verification_command_plan()
        for cmd in plan:
            assert "<<" not in cmd.command

    def test_commands_avoid_chained_git(self):
        plan = build_readonly_verification_command_plan()
        for cmd in plan:
            assert "git" not in cmd.command

    def test_deterministic(self):
        a = build_readonly_verification_command_plan()
        b = build_readonly_verification_command_plan()
        assert a == b

    def test_dataclass_frozen(self):
        cmd = build_readonly_verification_command_plan()[0]
        with pytest.raises(AttributeError):
            cmd.command_id = "mutated"

    def test_command_ids(self):
        plan = build_readonly_verification_command_plan()
        ids = [c.command_id for c in plan]
        assert ids == [
            "readonly-tests",
            "runtime-governance-tests",
            "governance-failure-tests",
            "core-regression",
            "full-readonly-bundle",
        ]


class TestToDict:
    def test_returns_list_of_dicts(self):
        plan = build_readonly_verification_command_plan()
        result = readonly_verification_command_plan_to_dict(plan)
        assert isinstance(result, list)
        assert len(result) == 5
        for d in result:
            assert isinstance(d, dict)
            assert set(d.keys()) == {"command_id", "command", "purpose", "required"}

    def test_values_match(self):
        plan = build_readonly_verification_command_plan()
        result = readonly_verification_command_plan_to_dict(plan)
        assert result[0]["command_id"] == "readonly-tests"
        assert result[0]["required"] is True
        assert result[-1]["required"] is False


class TestToMarkdown:
    def test_contains_command_id(self):
        plan = build_readonly_verification_command_plan()
        md = readonly_verification_command_plan_to_markdown(plan)
        for cmd in plan:
            assert cmd.command_id in md

    def test_contains_table_header(self):
        plan = build_readonly_verification_command_plan()
        md = readonly_verification_command_plan_to_markdown(plan)
        assert "Command ID" in md
        assert "Purpose" in md
        assert "Required" in md

    def test_deterministic(self):
        plan = build_readonly_verification_command_plan()
        a = readonly_verification_command_plan_to_markdown(plan)
        b = readonly_verification_command_plan_to_markdown(plan)
        assert a == b
