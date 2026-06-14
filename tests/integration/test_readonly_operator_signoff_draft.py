"""Integration test: read-only operator signoff draft."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_release_gate.operator_signoff_draft import create_draft


def test_signoff_draft_ready():
    draft = create_draft()
    assert "READONLY_DISCOVERY_OPERATOR_SIGNOFF_DRAFT_READY" in draft.final_verdict


def test_signoff_draft_has_pending():
    draft = create_draft()
    pending = [s for s in draft.sections if s.status == "PENDING"]
    assert len(pending) >= 1


def test_signoff_draft_section_count():
    draft = create_draft()
    assert len(draft.sections) >= 6
