"""T1350 - Status compatibility tests for frozen backlog."""
from __future__ import annotations

import os
import glob

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
DEV_PRD_DIR = os.path.join(DOCS_DIR, "dev_prd")
CORE_DIR = os.path.join(REPO_ROOT, "core")


class TestFrozenBacklogStatusCompatibility:
    def test_frozen_backlog_docs_exist(self):
        pattern = os.path.join(DEV_PRD_DIR, "frozen_backlog_*.md")
        docs = glob.glob(pattern)
        assert len(docs) >= 5, (
            f"Expected at least 5 frozen_backlog docs, found {len(docs)}"
        )

    def test_release_hold_is_hold(self):
        overview = os.path.join(DEV_PRD_DIR, "frozen_backlog_review_overview.md")
        assert os.path.isfile(overview), "Missing frozen_backlog_review_overview.md"
        with open(overview, encoding="utf-8") as f:
            content = f.read()
        assert "HOLD" in content, "frozen_backlog_review_overview.md must contain HOLD"
        assert "release_hold" in content.lower() or "release_hold" in content, (
            "Must reference release_hold"
        )

    def test_22_frozen_items_referenced(self):
        inventory = os.path.join(DOCS_DIR, "remaining_high_risk_frozen_inventory.md")
        assert os.path.isfile(inventory), "Missing remaining_high_risk_frozen_inventory.md"
        with open(inventory, encoding="utf-8") as f:
            content = f.read()
        assert "22" in content, "remaining_high_risk_frozen_inventory.md must reference 22 frozen items"

    def test_no_live_submit_exchange_in_core_models(self):
        """Verify core model files do not contain live/submit/exchange runtime terms."""
        model_prefixes = [
            "frozen_backlog_",
            "medium_operational_",
            "verification_script_",
            "human_approval_",
        ]
        forbidden = ("live_submit", "exchange_connect", "order_submit")
        violations: list[str] = []
        for prefix in model_prefixes:
            pattern = os.path.join(CORE_DIR, f"{prefix}*.py")
            for filepath in glob.glob(pattern):
                basename = os.path.basename(filepath)
                # Skip renderer files — only check model files
                if "renderer" in basename:
                    continue
                with open(filepath, encoding="utf-8") as f:
                    content = f.read()
                for term in forbidden:
                    if term in content:
                        violations.append(f"{basename}: contains '{term}'")
        assert not violations, f"Forbidden terms found: {violations}"
