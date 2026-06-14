"""Integration test: no-submit release archive."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.no_submit_release_archive import create_archive


def test_archive_ready():
    archive = create_archive()
    assert "NO_SUBMIT_RELEASE_ARCHIVE_READY" in archive.final_verdict


def test_all_entries_archived():
    archive = create_archive()
    assert all(e.status == "ARCHIVED" for e in archive.entries)


def test_archive_entry_count():
    archive = create_archive()
    assert len(archive.entries) >= 10
