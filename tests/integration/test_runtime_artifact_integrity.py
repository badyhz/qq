"""Integration tests for artifact integrity."""
from __future__ import annotations
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.artifacts.artifact_manifest import scan_artifacts, EXPECTED_ARTIFACTS
from src.runtime_integrations.artifacts.artifact_validator import validate


def test_scan_finds_all_artifacts():
    entries = scan_artifacts(ROOT)
    present = [e for e in entries if e.size_bytes > 0]
    assert len(present) == len(EXPECTED_ARTIFACTS)


def test_all_artifacts_parseable():
    entries = scan_artifacts(ROOT)
    for e in entries:
        if e.size_bytes > 0:
            assert e.parseable, f"{e.path} not parseable"


def test_all_artifacts_have_hashes():
    entries = scan_artifacts(ROOT)
    for e in entries:
        if e.size_bytes > 0:
            assert len(e.sha256) == 64


def test_validation_passes():
    entries = scan_artifacts(ROOT)
    result = validate(entries)
    assert result.all_valid
