"""Integration test: no-submit release archive (per-module)."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_final_governance_freeze.no_submit_release_archive import (
    create_archive, NoSubmitReleaseArchive
)


def test_archive_ready():
    archive = create_archive()
    assert "NO_SUBMIT_RELEASE_ARCHIVE_READY" in archive.final_verdict


def test_submit_prohibited():
    archive = create_archive()
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in archive.final_verdict


def test_real_network_blocked():
    archive = create_archive()
    assert "REAL_NETWORK_NOT_ALLOWED" in archive.final_verdict


def test_all_artifacts_archived():
    archive = create_archive()
    assert all(e.status == "ARCHIVED" for e in archive.entries)


def test_entry_count():
    archive = create_archive()
    assert len(archive.entries) >= 8


def test_covers_all_stages():
    archive = create_archive()
    stages = [e.stage for e in archive.entries]
    # Should cover T155 through T320 ranges
    assert any("T155" in s for s in stages)
    assert any("T320" in s for s in stages)


def test_release_mode_review_archive_only():
    archive = create_archive()
    # All entries are archived, none are LIVE or ACTIVE
    for e in archive.entries:
        assert e.status in ("ARCHIVED",), f"Unexpected status: {e.status}"
