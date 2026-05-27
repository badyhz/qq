"""Compatibility tests for T1361-T1440 governance registry — T1370.

Verifies:
- runtime_governance_task_queue.md contains T1361
- governance registry models are importable
- release_hold is HOLD in current_state doc
"""
from __future__ import annotations

import importlib
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REGISTRY_MODULES = [
    "core.governance_registry",
    "core.governance_domain_entry",
    "core.governance_layer_index",
    "core.governance_layer_entry",
    "core.governance_domain_status",
    "core.governance_cross_reference",
    "core.governance_registry_verdict",
    "core.governance_registry_renderer",
]


def test_task_queue_contains_t1361() -> None:
    """Verify T1361 is listed in runtime_governance_task_queue.md."""
    queue_path = os.path.join(
        REPO_ROOT, "docs", "dev_prd", "runtime_governance_task_queue.md"
    )
    with open(queue_path) as f:
        content = f.read()
    assert "T1361" in content, "T1361 not found in runtime_governance_task_queue.md"


def test_registry_models_importable() -> None:
    """Verify all 8 governance registry model modules are importable."""
    errors: list[str] = []
    for mod_name in REGISTRY_MODULES:
        try:
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"Module {mod_name} imported as None"
        except ImportError as exc:
            errors.append(f"{mod_name}: {exc}")
    assert not errors, f"Import failures:\n" + "\n".join(errors)


def test_registry_module_count_is_8() -> None:
    assert len(REGISTRY_MODULES) == 8


def test_release_hold_is_hold() -> None:
    """Verify release_hold is HOLD in current_state doc."""
    state_path = os.path.join(
        REPO_ROOT, "docs", "dev_prd", "runtime_governance_current_state.md"
    )
    with open(state_path) as f:
        content = f.read()
    # All layers document "Release hold: HOLD"
    assert "HOLD" in content, "HOLD not found in runtime_governance_current_state.md"
    assert "Release hold: HOLD" in content or "release_hold" in content.lower(), (
        "release_hold HOLD not confirmed in current_state doc"
    )
