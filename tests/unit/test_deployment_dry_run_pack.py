"""Tests for T42001 — Deployment Dry-run Pack."""
from __future__ import annotations

import json
import pytest

from core.deployment_dry_run_pack import (
    REQUIRED_CORE_MODULES,
    REQUIRED_RUNNER_SCRIPTS,
    DEPLOYMENT_STEPS,
    RELEASE_HOLD_REQUIRED_DPK,
    DeploymentStep,
    build_deployment_steps,
    compute_pack_hash,
    render_deployment_checklist_markdown,
    render_deployment_manifest_markdown,
)


# --- Build steps ---

def test_build_steps_count():
    steps = build_deployment_steps()
    assert len(steps) == len(DEPLOYMENT_STEPS)


def test_all_steps_simulation_only():
    steps = build_deployment_steps()
    for s in steps:
        assert s.simulation_only is True


def test_all_steps_advisory_only():
    steps = build_deployment_steps()
    for s in steps:
        assert s.advisory_only is True


def test_all_steps_human_approval():
    steps = build_deployment_steps()
    for s in steps:
        assert s.human_approval_required is True


def test_no_steps_would_execute():
    steps = build_deployment_steps()
    for s in steps:
        assert s.would_execute is False
        assert s.would_modify_files is False
        assert s.would_install_deps is False
        assert s.would_start_services is False


# --- Frozen ---

def test_step_is_frozen():
    steps = build_deployment_steps()
    with pytest.raises(AttributeError):
        steps[0].step_name = "x"


# --- to_dict ---

def test_to_dict_json_serializable():
    steps = build_deployment_steps()
    for s in steps:
        json.dumps(s.to_dict())


# --- Hash ---

def test_hash_deterministic():
    steps = build_deployment_steps()
    h1 = compute_pack_hash(steps)
    h2 = compute_pack_hash(steps)
    assert h1 == h2


def test_hash_is_sha256():
    steps = build_deployment_steps()
    h = compute_pack_hash(steps)
    assert len(h) == 64


# --- Markdown ---

def test_checklist_has_header():
    steps = build_deployment_steps()
    md = render_deployment_checklist_markdown(steps)
    assert "# Deployment Dry-run Checklist" in md


def test_checklist_has_all_steps():
    steps = build_deployment_steps()
    md = render_deployment_checklist_markdown(steps)
    for s in steps:
        assert s.step_name in md


def test_checklist_has_core_modules():
    steps = build_deployment_steps()
    md = render_deployment_checklist_markdown(steps)
    assert "Required Core Modules" in md
    assert "core/alert_center.py" in md


def test_checklist_has_runner_scripts():
    steps = build_deployment_steps()
    md = render_deployment_checklist_markdown(steps)
    assert "Required Runner Scripts" in md
    assert "scripts/run_frozen_cleanup_governance.py" in md


def test_manifest_has_table():
    steps = build_deployment_steps()
    md = render_deployment_manifest_markdown(steps)
    assert "| Step | Name |" in md


# --- Module lists ---

def test_required_core_modules_count():
    assert len(REQUIRED_CORE_MODULES) == 25


def test_required_runner_scripts_count():
    assert len(REQUIRED_RUNNER_SCRIPTS) == 12


def test_all_core_modules_start_with_core():
    for m in REQUIRED_CORE_MODULES:
        assert m.startswith("core/")


def test_all_runner_scripts_start_with_scripts():
    for s in REQUIRED_RUNNER_SCRIPTS:
        assert s.startswith("scripts/")
