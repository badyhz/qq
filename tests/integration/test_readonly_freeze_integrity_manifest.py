"""Integration test: freeze integrity manifest."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.freeze_integrity_manifest import (
    create_manifest, FreezeIntegrityManifest
)


def test_manifest_ready():
    manifest = create_manifest()
    assert "FREEZE_INTEGRITY_MANIFEST_READY" in manifest.final_verdict


def test_all_artifact_references_non_empty():
    manifest = create_manifest()
    for c in manifest.checks:
        assert c.artifact, f"Empty artifact for {c.check_id}"


def test_statuses_safe_or_frozen():
    manifest = create_manifest()
    for c in manifest.checks:
        assert c.status in ("FROZEN", "SAFE"), f"Unexpected status: {c.status}"


def test_no_real_network_enabled():
    manifest = create_manifest()
    assert "NO_REAL_NETWORK" in manifest.final_verdict


def test_no_submit_allowed():
    manifest = create_manifest()
    assert "NO_SUBMIT_ALLOWED" in manifest.final_verdict


def test_all_checks_safe():
    manifest = create_manifest()
    assert all(c.safe for c in manifest.checks)


def test_check_count():
    manifest = create_manifest()
    assert len(manifest.checks) >= 6
