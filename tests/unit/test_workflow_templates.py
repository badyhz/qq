"""Tests for Workflow Templates."""
from __future__ import annotations

import os

import pytest


def test_templates_exist():
    template_dir = "automation/workflow_templates"
    assert os.path.isdir(template_dir)
    assert os.path.isfile(os.path.join(template_dir, "__init__.py"))


def test_template_names():
    from automation.workflow_templates import TEMPLATES
    assert "SAFE_READONLY_AUDIT" in TEMPLATES
    assert "GUARD_INJECTION_BATCH" in TEMPLATES
    assert "DOCS_SYNC_WAVE" in TEMPLATES
    assert "ENGINEERING_CLOSEOUT" in TEMPLATES


def test_template_structure():
    from automation.workflow_templates import TEMPLATES
    for name, template in TEMPLATES.items():
        assert "name" in template, f"{name} missing name"
        assert "description" in template, f"{name} missing description"
        assert "inputs" in template, f"{name} missing inputs"
        assert "outputs" in template, f"{name} missing outputs"
        assert "parallel_policy" in template, f"{name} missing parallel_policy"
        assert "validation_checklist" in template, f"{name} missing validation_checklist"
        assert "stop_conditions" in template, f"{name} missing stop_conditions"
        assert "anti_patterns" in template, f"{name} missing anti_patterns"


def test_parallel_policy_structure():
    from automation.workflow_templates import TEMPLATES
    for name, template in TEMPLATES.items():
        policy = template["parallel_policy"]
        assert "mode" in policy, f"{name} parallel_policy missing mode"
        assert "max_agents" in policy, f"{name} parallel_policy missing max_agents"
        assert "rules" in policy, f"{name} parallel_policy missing rules"
        assert isinstance(policy["rules"], list), f"{name} rules must be list"


def test_get_template():
    from automation.workflow_templates import get_template
    t = get_template("SAFE_READONLY_AUDIT")
    assert t["name"] == "SAFE_READONLY_AUDIT"


def test_get_template_unknown():
    from automation.workflow_templates import get_template
    with pytest.raises(ValueError, match="Unknown template"):
        get_template("NONEXISTENT")


def test_all_inputs_required():
    from automation.workflow_templates import TEMPLATES
    for name, template in TEMPLATES.items():
        for input_name, input_def in template["inputs"].items():
            assert "type" in input_def, f"{name}.inputs.{input_name} missing type"
            assert "required" in input_def, f"{name}.inputs.{input_name} missing required"
