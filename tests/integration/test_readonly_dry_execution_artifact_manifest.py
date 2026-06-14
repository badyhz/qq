"""Integration test: rehearsal artifact manifest."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_dry_execution_rehearsal.rehearsal_artifact_manifest import (
    create_manifest, RehearsalArtifactManifest
)


def test_manifest_ready():
    manifest = create_manifest()
    assert "REHEARSAL_ARTIFACT_MANIFEST_READY" in manifest.final_verdict


def test_rehearsal_artifact_present():
    manifest = create_manifest()
    names = [a.artifact_name for a in manifest.artifacts]
    assert "Dry execution rehearsal" in names


def test_endpoint_allowlist_artifact_present():
    manifest = create_manifest()
    names = [a.artifact_name for a in manifest.artifacts]
    assert "Endpoint allowlist stub" in names


def test_audit_redaction_artifact_present():
    manifest = create_manifest()
    names = [a.artifact_name for a in manifest.artifacts]
    assert "Audit redaction pack" in names


def test_safety_regression_artifact_present():
    manifest = create_manifest()
    names = [a.artifact_name for a in manifest.artifacts]
    assert "Safety regression" in names


def test_all_artifacts_present():
    manifest = create_manifest()
    assert all(a.status == "PRESENT" for a in manifest.artifacts)


def test_artifact_count():
    manifest = create_manifest()
    assert len(manifest.artifacts) >= 4
