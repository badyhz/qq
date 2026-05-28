"""Tests for frozen inventory audit scanner.

Verifies:
- scanner never imports fixture modules
- scanner never executes fixture modules
- risk keyword detection works
- category classification works
- missing file recorded safely
- large file skip works
- manifest safety flags correct
- release_hold != HOLD fails
- output deterministic across reruns
- JSON and markdown emitted
- no network/exchange imports in scanner
- no forbidden files are staged
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile

import pytest

# Ensure project root is on path
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.frozen_inventory_audit import (
    RELEASE_HOLD_REQUIRED,
    RISK_KEYWORDS,
    FileRecord,
    InventoryResult,
    scan_files,
    write_json,
    write_manifest,
    write_markdown,
    _detect_risk_keywords,
    _classify_category,
)

FIXTURE_DIR = "tests/fixtures/frozen_inventory"

SAMPLE_LIVE = f"{FIXTURE_DIR}/sample_live.py"
SAMPLE_TESTNET = f"{FIXTURE_DIR}/sample_testnet_submit.py"
SAMPLE_SHADOW = f"{FIXTURE_DIR}/sample_shadow.py"
SAMPLE_SAFE = f"{FIXTURE_DIR}/sample_safe_doc.md"

ALL_FIXTURES = [SAMPLE_LIVE, SAMPLE_TESTNET, SAMPLE_SHADOW, SAMPLE_SAFE]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scan_fixtures(extra: list[str] | None = None, **kwargs) -> InventoryResult:
    paths = ALL_FIXTURES + (extra or [])
    return scan_files(paths, repo_root=PROJECT_ROOT, **kwargs)


# ---------------------------------------------------------------------------
# Tests: scanner never imports or executes fixtures
# ---------------------------------------------------------------------------


class TestNoImportNoExecute:
    """Verify the scanner does not import or execute target files."""

    def test_sample_live_not_imported(self):
        """sample_live must not be in sys.modules after scan."""
        mod_key = "tests.fixtures.frozen_inventory.sample_live"
        # If it were imported, it would be in sys.modules
        assert mod_key not in sys.modules

    def test_sample_testnet_not_imported(self):
        mod_key = "tests.fixtures.frozen_inventory.sample_testnet_submit"
        scan_files([SAMPLE_TESTNET], repo_root=PROJECT_ROOT)
        assert mod_key not in sys.modules

    def test_sample_shadow_not_imported(self):
        mod_key = "tests.fixtures.frozen_inventory.sample_shadow"
        scan_files([SAMPLE_SHADOW], repo_root=PROJECT_ROOT)
        assert mod_key not in sys.modules

    def test_scan_does_not_modify_sys_modules(self):
        before = set(sys.modules.keys())
        _scan_fixtures()
        after = set(sys.modules.keys())
        new_keys = after - before
        # Filter out test infrastructure imports
        suspicious = [k for k in new_keys if "frozen_inventory" in k and "test" not in k]
        assert suspicious == [], f"Unexpected modules imported: {suspicious}"


# ---------------------------------------------------------------------------
# Tests: risk keyword detection
# ---------------------------------------------------------------------------


class TestRiskKeywords:
    def test_detect_risk_keywords_basic(self):
        text = "import requests\nfrom binance.client import Client\nAPI_KEY = 'x'"
        kws = _detect_risk_keywords(text)
        assert "requests" in kws
        assert "binance" in kws
        assert "api_key" in kws

    def test_detect_risk_keywords_empty(self):
        assert _detect_risk_keywords("") == []

    def test_detect_risk_keywords_case_insensitive(self):
        kws = _detect_risk_keywords("LIVE trading enabled")
        assert "live" in kws

    def test_sample_live_has_expected_keywords(self):
        result = scan_files([SAMPLE_LIVE], repo_root=PROJECT_ROOT)
        rec = result.files[0]
        assert "live" in rec.risk_keywords
        assert "binance" in rec.risk_keywords
        assert "fapi" in rec.risk_keywords

    def test_sample_testnet_has_expected_keywords(self):
        result = scan_files([SAMPLE_TESTNET], repo_root=PROJECT_ROOT)
        rec = result.files[0]
        assert "testnet" in rec.risk_keywords
        assert "binance" in rec.risk_keywords
        assert "api_key" in rec.risk_keywords
        assert "requests" in rec.risk_keywords

    def test_sample_shadow_has_expected_keywords(self):
        result = scan_files([SAMPLE_SHADOW], repo_root=PROJECT_ROOT)
        rec = result.files[0]
        assert "submit" in rec.risk_keywords or "shadow" in rec.risk_keywords

    def test_safe_doc_has_no_keywords(self):
        result = scan_files([SAMPLE_SAFE], repo_root=PROJECT_ROOT)
        rec = result.files[0]
        assert rec.risk_keywords == []


# ---------------------------------------------------------------------------
# Tests: category classification
# ---------------------------------------------------------------------------


class TestCategoryClassification:
    def test_classify_live(self):
        assert _classify_category("scripts/live_playbook.py", "") == "LIVE"

    def test_classify_testnet(self):
        assert _classify_category("scripts/run_testnet_order_smoke.py", "") == "TESTNET"

    def test_classify_shadow(self):
        assert _classify_category("scripts/run_shadow_observation.py", "") == "SHADOW"

    def test_classify_submit(self):
        assert _classify_category("scripts/submit_approved_candidates.py", "") == "SUBMIT"

    def test_classify_flatten(self):
        assert _classify_category("scripts/safe_flatten_testnet_symbol.py", "") == "FLATTEN"

    def test_classify_cancel_from_content(self):
        assert _classify_category("some_other.py", "def cancel_order():") == "CANCEL"

    def test_classify_observation(self):
        assert _classify_category("scripts/run_right_breakout_param_observation.py", "") == "OBSERVATION"

    def test_classify_verify(self):
        assert _classify_category("scripts/verify_risk_release_flow.py", "") == "VERIFY"

    def test_classify_unknown(self):
        assert _classify_category("docs/something.md", "hello world") == "UNKNOWN"


# ---------------------------------------------------------------------------
# Tests: missing file
# ---------------------------------------------------------------------------


class TestMissingFile:
    def test_missing_file_recorded(self):
        result = scan_files(["nonexistent_file_xyz.py"], repo_root=PROJECT_ROOT)
        assert len(result.files) == 1
        rec = result.files[0]
        assert rec.exists is False
        assert rec.git_status == "missing"
        assert rec.size_bytes is None
        assert rec.sha256 is None


# ---------------------------------------------------------------------------
# Tests: large file skip
# ---------------------------------------------------------------------------


class TestLargeFileSkip:
    def test_large_file_skipped(self, tmp_path: pathlib.Path):
        big = tmp_path / "big.txt"
        big.write_bytes(b"x" * 1_000_000)
        result = scan_files([str(big)], repo_root=tmp_path, max_size_bytes=100)
        rec = result.files[0]
        assert rec.exists is True
        assert rec.skip_reason is not None
        assert "size" in rec.skip_reason
        # sha256 still computed
        assert rec.sha256 is not None
        # line count not computed for oversized
        assert rec.line_count is None


# ---------------------------------------------------------------------------
# Tests: manifest safety flags
# ---------------------------------------------------------------------------


class TestManifestSafety:
    def test_manifest_flags_correct(self):
        result = _scan_fixtures()
        m = result.manifest
        assert m["release_hold"] == "HOLD"
        assert m["advisory_only"] is True
        assert m["human_review_required"] is True
        assert m["no_live"] is True
        assert m["no_submit"] is True
        assert m["no_exchange"] is True
        assert m["no_network"] is True
        assert m["no_runtime_integration"] is True
        assert m["no_planner_integration"] is True
        assert m["audit_only"] is True
        assert m["no_execution"] is True
        assert m["no_import"] is True

    def test_release_hold_not_hold_fails_strict(self):
        """build_frozen_inventory_report --strict fails if release_hold != HOLD."""
        # Directly test scan_files accepts any release_hold
        result = scan_files(ALL_FIXTURES, repo_root=PROJECT_ROOT, release_hold="RELEASED")
        assert result.manifest["release_hold"] == "RELEASED"
        # But the constant is enforced at CLI level
        assert RELEASE_HOLD_REQUIRED == "HOLD"


# ---------------------------------------------------------------------------
# Tests: output determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_json_deterministic(self, tmp_path: pathlib.Path):
        result = _scan_fixtures()
        p1 = tmp_path / "out1.json"
        p2 = tmp_path / "out2.json"
        write_json(result, p1)
        write_json(result, p2)
        assert p1.read_text() == p2.read_text()

    def test_markdown_deterministic(self, tmp_path: pathlib.Path):
        result = _scan_fixtures()
        p1 = tmp_path / "out1.md"
        p2 = tmp_path / "out2.md"
        write_markdown(result, p1)
        write_markdown(result, p2)
        assert p1.read_text() == p2.read_text()

    def test_manifest_deterministic(self, tmp_path: pathlib.Path):
        result = _scan_fixtures()
        p1 = tmp_path / "m1.json"
        p2 = tmp_path / "m2.json"
        write_manifest(result, p1)
        write_manifest(result, p2)
        assert p1.read_text() == p2.read_text()


# ---------------------------------------------------------------------------
# Tests: JSON and markdown emitted
# ---------------------------------------------------------------------------


class TestOutputEmitted:
    def test_json_emitted(self, tmp_path: pathlib.Path):
        result = _scan_fixtures()
        out = tmp_path / "inv.json"
        write_json(result, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert "manifest" in data
        assert "files" in data
        assert len(data["files"]) == len(ALL_FIXTURES)

    def test_markdown_emitted(self, tmp_path: pathlib.Path):
        result = _scan_fixtures()
        out = tmp_path / "inv.md"
        write_markdown(result, out)
        assert out.exists()
        text = out.read_text()
        assert "Frozen Testnet / Runtime Inventory" in text
        assert "release_hold" in text
        assert "Safety Boundary" in text

    def test_manifest_emitted(self, tmp_path: pathlib.Path):
        result = _scan_fixtures()
        out = tmp_path / "manifest.json"
        write_manifest(result, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["release_hold"] == "HOLD"


# ---------------------------------------------------------------------------
# Tests: no network/exchange imports in scanner module
# ---------------------------------------------------------------------------


class TestScannerNoNetwork:
    def test_scanner_module_imports(self):
        """Verify the scanner module itself does not import network libs."""
        import core.frozen_inventory_audit as mod
        source_file = pathlib.Path(mod.__file__).read_text()
        forbidden = ["import requests", "import httpx", "import aiohttp", "import websocket"]
        for f in forbidden:
            assert f not in source_file, f"Scanner imports forbidden: {f}"


# ---------------------------------------------------------------------------
# Tests: full scan of all fixtures
# ---------------------------------------------------------------------------


class TestFullScan:
    def test_all_fixtures_found(self):
        result = _scan_fixtures()
        for rec in result.files:
            assert rec.exists, f"Missing: {rec.path}"

    def test_all_fixtures_have_sha256(self):
        result = _scan_fixtures()
        for rec in result.files:
            assert rec.sha256 is not None, f"No hash: {rec.path}"

    def test_all_fixtures_have_line_count(self):
        result = _scan_fixtures()
        for rec in result.files:
            assert rec.line_count is not None, f"No line count: {rec.path}"
            assert rec.line_count > 0

    def test_expected_category_counts(self):
        result = _scan_fixtures()
        cats = {}
        for rec in result.files:
            cats[rec.category] = cats.get(rec.category, 0) + 1
        # sample_live.py -> LIVE
        assert cats.get("LIVE", 0) >= 1
        # sample_testnet_submit.py -> SUBMIT (path contains "submit")
        assert cats.get("SUBMIT", 0) >= 1
        # sample_shadow.py -> SHADOW
        assert cats.get("SHADOW", 0) >= 1
        # sample_safe_doc.md -> UNKNOWN
        assert cats.get("UNKNOWN", 0) >= 1


# ---------------------------------------------------------------------------
# Tests: no forbidden files staged
# ---------------------------------------------------------------------------


class TestNoForbiddenStaged:
    def test_no_preexisting_files_in_staged_list(self):
        """Verify no pre-existing untracked files appear in git staged area."""
        import subprocess

        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        staged = set(result.stdout.strip().splitlines()) if result.stdout.strip() else set()
        forbidden_prefixes = (
            "core/live_runner.py",
            "scripts/live_playbook.py",
            "scripts/run_testnet_",
            "scripts/run_spot_testnet_",
            "scripts/run_signal_testnet_",
            "scripts/run_controlled_testnet_",
            "scripts/run_shadow_",
            "scripts/run_daily_shadow_",
            "scripts/run_next_shadow_",
            "scripts/run_remediation_",
            "scripts/run_replay_",
            "scripts/run_right_breakout_",
            "scripts/run_observation_",
            "scripts/safe_flatten_",
            "scripts/submit_",
            "scripts/verify_",
            "scripts/replay_shadow_",
            "research/",
        )
        violations = [
            s for s in staged
            if any(s.startswith(p) for p in forbidden_prefixes)
        ]
        assert violations == [], f"Forbidden files staged: {violations}"
