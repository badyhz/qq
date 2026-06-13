"""Test operator emergency procedure."""
import pytest
from src.runtime_integrations.testnet_presubmit.operator_emergency_procedure import get_steps, validate_procedure

def test_steps_exist():
    steps = get_steps()
    assert len(steps) >= 10

def test_procedure_valid():
    steps = get_steps()
    valid, errors = validate_procedure(steps)
    assert valid is True
    assert len(errors) == 0

def test_steps_have_required_fields():
    for s in get_steps():
        assert s.step_id
        assert s.title
        assert s.description
        assert s.required is True
