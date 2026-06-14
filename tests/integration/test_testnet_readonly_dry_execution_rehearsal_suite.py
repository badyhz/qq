"""Integration test: testnet read-only dry execution rehearsal suite runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.dry_execution_rehearsal import create_rehearsal
from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.endpoint_allowlist_stub import create_stub
from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.audit_redaction_pack import create_pack
from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.dry_execution_safety_regression import run_regression


def test_rehearsal_ready():
    reh = create_rehearsal()
    assert "READONLY_DRY_EXECUTION_REHEARSAL_READY" in reh.final_verdict


def test_allowlist_ready():
    stub = create_stub()
    assert "ENDPOINT_ALLOWLIST_STUB_READY" in stub.final_verdict


def test_redaction_ready():
    pack = create_pack()
    assert "AUDIT_REDACTION_PACK_READY" in pack.final_verdict


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
