"""Integration test: testnet read-only PRD compliance correction suite."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_approval_simulator.network_on_blocker_drill import (
    create_drill as create_blocker_drill, has_unblocked_case
)
from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.rehearsal_artifact_manifest import (
    create_manifest as create_rehearsal_manifest
)
from src.runtime_integrations.testnet_readonly_final_governance_freeze.freeze_integrity_manifest import (
    create_manifest as create_freeze_manifest
)
from src.runtime_integrations.testnet_readonly_scope_audit.de_facto_spec_registry import create_registry
from src.runtime_integrations.testnet_readonly_scope_audit.remediation_backlog import create_backlog
from src.runtime_integrations.testnet_readonly_scope_audit.scope_audit_safety_regression import run_regression


def test_blocker_drill_expanded():
    drill = create_blocker_drill()
    assert len(drill.scenarios) >= 15
    assert "NETWORK_ON_BLOCKER_DRILL_EXPANDED" in drill.final_verdict
    assert has_unblocked_case(drill.scenarios) is False


def test_rehearsal_manifest_ready():
    manifest = create_rehearsal_manifest()
    assert "REHEARSAL_ARTIFACT_MANIFEST_READY" in manifest.final_verdict


def test_freeze_manifest_ready():
    manifest = create_freeze_manifest()
    assert "FREEZE_INTEGRITY_MANIFEST_READY" in manifest.final_verdict


def test_de_facto_spec_registry_ready():
    registry = create_registry()
    assert "DE_FACTO_SPEC_REGISTRY_READY" in registry.final_verdict
    assert len(registry.entries) == 6


def test_remediation_backlog_updated():
    backlog = create_backlog()
    rem002 = [i for i in backlog.items if i.task_id == "REM_002"][0]
    assert "Expanded in T325001-T335000" in rem002.recommended_fix
    rem003 = [i for i in backlog.items if i.task_id == "REM_003"][0]
    assert "Test split completed in T325001-T335000" in rem003.recommended_fix


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
