"""Integration test: readonly tag chain manifest."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_checkpoint.tag_chain_manifest import create_manifest


def test_manifest_ready():
    manifest = create_manifest()
    assert "READONLY_TAG_CHAIN_MANIFEST_READY" in manifest.final_verdict


def test_all_tags_present():
    manifest = create_manifest()
    assert manifest.all_present is True
    assert all(e.present for e in manifest.entries)


def test_tag_count():
    manifest = create_manifest()
    assert manifest.total_tags == 13


def test_required_tags_present():
    manifest = create_manifest()
    tags = {e.tag for e in manifest.entries}
    required = [
        "external-testnet-adapter-spec-complete",
        "testnet-readonly-discovery-design-complete",
        "testnet-readonly-final-governance-freeze-complete",
        "testnet-readonly-prd-compliance-correction-complete",
    ]
    for t in required:
        assert t in tags, f"Missing required tag: {t}"


def test_chain_unbroken():
    manifest = create_manifest()
    assert "CHAIN_UNBROKEN" in manifest.final_verdict
