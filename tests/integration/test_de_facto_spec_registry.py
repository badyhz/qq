"""Integration test: de facto spec registry."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_scope_audit.de_facto_spec_registry import (
    create_registry, DeFactoSpecRegistry
)


def test_registry_ready():
    registry = create_registry()
    assert "DE_FACTO_SPEC_REGISTRY_READY" in registry.final_verdict


def test_all_stages_documented():
    registry = create_registry()
    stages = [e.stage_id for e in registry.entries]
    for i in range(1, 7):
        assert f"STG_RO_{i:03d}" in stages


def test_all_implementations_as_spec():
    registry = create_registry()
    for e in registry.entries:
        assert e.spec_source_type == "IMPLEMENTATION_AS_DE_FACTO_SPEC"


def test_all_complete():
    registry = create_registry()
    for e in registry.entries:
        assert e.status == "COMPLETE"


def test_entry_count():
    registry = create_registry()
    assert len(registry.entries) == 6


def test_external_prd_not_found():
    registry = create_registry()
    assert "EXTERNAL_PRD_NOT_FOUND" in registry.final_verdict
