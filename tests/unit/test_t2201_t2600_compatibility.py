"""T2201-T2600 closeout compatibility tests."""
import os
import pytest

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "dev_prd")

CLOSEOUT_DOCS = [
    "t2201_t2600_unit_failure_triage_report.md",
    "t2201_t2600_safe_fix_log.md",
    "t2201_t2600_remaining_failure_inventory.md",
    "t2201_t2600_final_closeout_report.md",
]


class TestT2201T2600CloseoutDocsExist:
    """All closeout docs must exist."""

    @pytest.mark.parametrize("doc", CLOSEOUT_DOCS)
    def test_doc_exists(self, doc):
        path = os.path.join(DOCS_DIR, doc)
        assert os.path.isfile(path), f"Missing: {path}"


class TestTaskQueueReferences:
    """Task queue must reference T2201 and T2600."""

    def _read_task_queue(self):
        path = os.path.join(DOCS_DIR, "runtime_governance_task_queue.md")
        with open(path, "r") as f:
            return f.read()

    def test_references_t2201(self):
        content = self._read_task_queue()
        assert "T2201" in content, "Task queue does not reference T2201"

    def test_references_t2600(self):
        content = self._read_task_queue()
        assert "T2600" in content, "Task queue does not reference T2600"

    def test_t2201_t2600_completed(self):
        content = self._read_task_queue()
        assert "T2201-T2600" in content, "Task queue missing T2201-T2600 range"
        assert "completed" in content.lower()


class TestReleaseHold:
    """release_hold must still be HOLD."""

    def _read_closeout_report(self):
        path = os.path.join(DOCS_DIR, "t2201_t2600_final_closeout_report.md")
        with open(path, "r") as f:
            return f.read()

    def test_release_hold_is_hold(self):
        content = self._read_closeout_report()
        assert "HOLD" in content, "release_hold is not HOLD"

    def test_no_live_trading(self):
        content = self._read_closeout_report()
        assert "No live trading" in content
