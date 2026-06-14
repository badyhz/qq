"""Integration test: read-only human signoff archive."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_approval_simulator.human_signoff_archive import create_archive


def test_archive_ready():
    archive = create_archive()
    assert "READONLY_HUMAN_SIGNOFF_ARCHIVE_READY" in archive.final_verdict


def test_archive_has_records():
    archive = create_archive()
    assert len(archive.records) >= 6


def test_archive_all_phases_documented():
    archive = create_archive()
    phases = [r.phase for r in archive.records]
    assert len(set(phases)) >= 5
